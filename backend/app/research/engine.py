import asyncio
import json
import logging
import traceback

from anthropic import AsyncAnthropic

from app.api.projects import emit_event
from app.config import settings
from app.database import get_db
from app.models import Requirement
from app.research.deep import deep_research
from app.research.fallback import resolve_fallback
from app.research.parse import parse_prompt
from app.research.score import compute_scores
from app.research.wide import deduplicate_options, wide_search

logger = logging.getLogger(__name__)

WIDE_SEMAPHORE = asyncio.Semaphore(5)
DEEP_SEMAPHORE = asyncio.Semaphore(5)
FALLBACK_SEMAPHORE = asyncio.Semaphore(3)


async def _set_status(project_id: str, status: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE projects SET status = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (status, project_id),
        )
        await db.commit()
    finally:
        await db.close()
    await emit_event(project_id, "phase_change", {"phase": status, "message": f"Phase: {status}"})


async def _log_llm_call(
    project_id: str,
    phase: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    summary: str,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO llm_calls "
            "(project_id, phase, model, input_tokens, output_tokens, duration_ms, request_summary) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, phase, model, input_tokens, output_tokens, duration_ms, summary),
        )
        await db.commit()
    finally:
        await db.close()


async def _load_reqs(project_id: str) -> list[Requirement]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM project_requirements WHERE project_id = ? ORDER BY sort_order",
            (project_id,),
        )
        return [
            Requirement(
                id=r["id"],
                project_id=r["project_id"],
                key=r["key"],
                label=r["label"],
                type=r["type"],
                enum_options=r["enum_options"],
                unit=r["unit"],
                is_hard=bool(r["is_hard"]),
                weight=r["weight"],
                direction=r["direction"],
                sort_order=r["sort_order"],
            )
            for r in await cursor.fetchall()
        ]
    finally:
        await db.close()


async def run_research(project_id: str) -> None:
    """Main research orchestrator. Supports resuming from where it left off."""
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        # Check existing state to decide where to resume
        db = await get_db()
        try:
            cursor = await db.execute("SELECT prompt FROM projects WHERE id = ?", (project_id,))
            row = await cursor.fetchone()
            assert row is not None
            prompt = row["prompt"]

            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM project_requirements WHERE project_id = ?",
                (project_id,),
            )
            has_requirements = (await cursor.fetchone())["cnt"] > 0

            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM listings WHERE project_id = ?",
                (project_id,),
            )
            has_listings = (await cursor.fetchone())["cnt"] > 0
        finally:
            await db.close()

        # --- Phase 1: Parse (skip if we already have requirements) ---
        if not has_requirements:
            await _set_status(project_id, "parsing")
            result = await parse_prompt(client, prompt)
            await _log_llm_call(
                project_id,
                "parse",
                settings.model,
                result.input_tokens,
                result.output_tokens,
                result.duration_ms,
                "Parse prompt",
            )
            db = await get_db()
            try:
                await db.execute(
                    "UPDATE projects SET parsed_intent = ?, search_locale = ? WHERE id = ?",
                    (result.parsed_intent, result.search_locale, project_id),
                )
                for i, req in enumerate(result.requirements):
                    enum_opts = json.dumps(req.get("enum_options")) if req.get("enum_options") else None
                    await db.execute(
                        "INSERT INTO project_requirements "
                        "(project_id, key, label, type, enum_options, unit, "
                        "is_hard, weight, direction, sort_order) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            project_id,
                            req["key"],
                            req["label"],
                            req["type"],
                            enum_opts,
                            req.get("unit"),
                            int(req.get("is_hard", False)),
                            req.get("weight", 1.0),
                            req.get("direction", "higher_better"),
                            i,
                        ),
                    )
                for query_text in result.search_queries:
                    await db.execute(
                        "INSERT INTO search_queries (project_id, query_text, phase) VALUES (?, ?, 'wide')",
                        (project_id, query_text),
                    )
                await db.commit()
            finally:
                await db.close()

            await emit_event(
                project_id,
                "parse_complete",
                {
                    "parsed_intent": result.parsed_intent,
                    "requirements_count": len(result.requirements),
                    "queries_count": len(result.search_queries),
                },
            )
        else:
            await emit_event(
                project_id,
                "phase_change",
                {
                    "phase": "parse_skipped",
                    "message": "Resuming: parse already complete, skipping",
                },
            )

        # --- Phase 2: Wide search (skip queries already completed) ---
        await _set_status(project_id, "searching")

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT id, query_text FROM search_queries "
                "WHERE project_id = ? AND phase = 'wide' AND status = 'pending'",
                (project_id,),
            )
            pending_queries = await cursor.fetchall()
        finally:
            await db.close()

        if not pending_queries and has_listings:
            await emit_event(
                project_id,
                "phase_change",
                {
                    "phase": "wide_skipped",
                    "message": f"Resuming: wide search already done, {has_listings} existing listings",
                },
            )
        else:

            async def _run_wide(query_text: str, query_id: int):
                async with WIDE_SEMAPHORE:
                    try:
                        await emit_event(
                            project_id,
                            "search_started",
                            {
                                "query": query_text,
                                "query_id": query_id,
                            },
                        )

                        # Load project's search locale
                        db_inner = await get_db()
                        try:
                            cursor = await db_inner.execute(
                                "SELECT parsed_intent, search_locale FROM projects WHERE id = ?",
                                (project_id,),
                            )
                            proj = await cursor.fetchone()
                        finally:
                            await db_inner.close()

                        wr = await wide_search(
                            client,
                            query_text,
                            proj["parsed_intent"] or "options",
                            proj["search_locale"],
                        )
                        await _log_llm_call(
                            project_id,
                            "wide",
                            settings.model,
                            wr.input_tokens,
                            wr.output_tokens,
                            wr.duration_ms,
                            f"Wide search: {query_text[:80]}",
                        )
                        db2 = await get_db()
                        try:
                            await db2.execute(
                                "UPDATE search_queries SET status = 'complete', result_count = ? WHERE id = ?",
                                (len(wr.options), query_id),
                            )
                            await db2.commit()
                        finally:
                            await db2.close()

                        option_names = [o.get("name", "?") for o in wr.options]
                        await emit_event(
                            project_id,
                            "search_executed",
                            {
                                "query": query_text,
                                "results": len(wr.options),
                                "names": option_names,
                                "tokens": wr.input_tokens + wr.output_tokens,
                                "duration_s": round(wr.duration_ms / 1000, 1),
                            },
                        )
                        return wr.options
                    except Exception as exc:
                        logger.exception("Wide search failed for: %s", query_text)
                        await emit_event(
                            project_id,
                            "search_error",
                            {
                                "query": query_text,
                                "error": str(exc),
                            },
                        )
                        return []

            tasks = [_run_wide(q["query_text"], q["id"]) for q in pending_queries]
            results_list = await asyncio.gather(*tasks)

            all_options: list[dict[str, str | None]] = []
            for opts in results_list:
                all_options.extend(opts)
            unique_options = deduplicate_options(all_options)

            await emit_event(
                project_id,
                "dedup_complete",
                {
                    "total_found": len(all_options),
                    "unique": len(unique_options),
                    "duplicates_removed": len(all_options) - len(unique_options),
                },
            )

            # Insert discovered listings
            db = await get_db()
            try:
                for opt in unique_options:
                    cursor = await db.execute(
                        "INSERT INTO listings (project_id, name, url, address, summary) VALUES (?, ?, ?, ?, ?)",
                        (
                            project_id,
                            opt.get("name", "Unknown"),
                            opt.get("url"),
                            opt.get("address"),
                            opt.get("snippet"),
                        ),
                    )
                    listing_id = cursor.lastrowid
                    await emit_event(
                        project_id,
                        "listing_discovered",
                        {
                            "id": listing_id,
                            "name": opt.get("name", "Unknown"),
                            "url": opt.get("url"),
                        },
                    )
                await db.commit()
            finally:
                await db.close()

        # --- Phase 3: Deep research (only on undone listings) ---
        await _set_status(project_id, "researching")
        reqs = await _load_reqs(project_id)

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT id, name, url, address FROM listings WHERE project_id = ? AND status = 'discovered'",
                (project_id,),
            )
            undone = await cursor.fetchall()

            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM listings WHERE project_id = ? AND status = 'complete'",
                (project_id,),
            )
            already_done = (await cursor.fetchone())["cnt"]
        finally:
            await db.close()

        if not undone and already_done > 0:
            await emit_event(
                project_id,
                "phase_change",
                {
                    "phase": "deep_skipped",
                    "message": f"Resuming: all {already_done} listings already researched",
                },
            )
        else:
            await emit_event(
                project_id,
                "deep_started",
                {
                    "total": len(undone),
                    "already_done": already_done,
                    "names": [row["name"] for row in undone],
                },
            )

            async def _run_deep(listing_row):
                async with DEEP_SEMAPHORE:
                    lid = listing_row["id"]
                    try:
                        await emit_event(
                            project_id,
                            "deep_researching",
                            {
                                "id": lid,
                                "name": listing_row["name"],
                            },
                        )
                        dr = await deep_research(
                            client,
                            listing_row["name"],
                            listing_row["url"],
                            listing_row["address"],
                            reqs,
                        )
                        await _log_llm_call(
                            project_id,
                            "deep",
                            settings.model,
                            dr.input_tokens,
                            dr.output_tokens,
                            dr.duration_ms,
                            f"Deep research: {listing_row['name'][:60]}",
                        )
                        db2 = await get_db()
                        try:
                            await db2.execute(
                                "UPDATE listings SET attributes = ?, summary = ?, "
                                "image_url = COALESCE(?, image_url), "
                                "raw_notes = ?, status = 'complete' WHERE id = ?",
                                (
                                    json.dumps(dr.attributes),
                                    dr.summary,
                                    dr.image_url,
                                    dr.raw_notes,
                                    lid,
                                ),
                            )
                            if dr.attribute_confidence:
                                conf_note = "\n\n---CONFIDENCE---\n" + json.dumps(dr.attribute_confidence)
                                await db2.execute(
                                    "UPDATE listings SET raw_notes = COALESCE(raw_notes, '') || ? WHERE id = ?",
                                    (conf_note, lid),
                                )
                            await db2.commit()
                        finally:
                            await db2.close()
                        filled = sum(1 for v in dr.attributes.values() if v is not None)
                        await emit_event(
                            project_id,
                            "listing_updated",
                            {
                                "id": lid,
                                "name": listing_row["name"],
                                "status": "complete",
                                "filled": f"{filled}/{len(reqs)}",
                                "summary": (dr.summary or "")[:120],
                                "tokens": dr.input_tokens + dr.output_tokens,
                                "duration_s": round(dr.duration_ms / 1000, 1),
                            },
                        )
                    except Exception:
                        logger.exception("Deep research failed for listing %d", lid)
                        db2 = await get_db()
                        try:
                            await db2.execute(
                                "UPDATE listings SET status = 'error' WHERE id = ?",
                                (lid,),
                            )
                            await db2.commit()
                        finally:
                            await db2.close()

            deep_tasks = [_run_deep(listing) for listing in undone]
            await asyncio.gather(*deep_tasks)

        # --- Phase 4: Fallback resolution ---
        await _set_status(project_id, "resolving")

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT id, name, address, attributes FROM listings "
                "WHERE project_id = ? AND status = 'complete' "
                "ORDER BY score DESC NULLS LAST LIMIT 10",
                (project_id,),
            )
            fallback_candidates = await cursor.fetchall()
        finally:
            await db.close()

        async def _run_fallback(listing_row, req: Requirement):
            async with FALLBACK_SEMAPHORE:
                try:
                    fr = await resolve_fallback(
                        client,
                        listing_row["name"],
                        listing_row["address"],
                        req.label,
                    )
                    await _log_llm_call(
                        project_id,
                        "fallback",
                        settings.model,
                        fr.input_tokens,
                        fr.output_tokens,
                        fr.duration_ms,
                        f"Fallback: {listing_row['name'][:40]} / {req.label}",
                    )
                    db2 = await get_db()
                    try:
                        for alt in fr.alternatives:
                            await db2.execute(
                                "INSERT INTO fallbacks "
                                "(listing_id, requirement_key, resolution_name, "
                                "resolution_detail, resolution_url, "
                                "distance_meters, satisfies) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (
                                    listing_row["id"],
                                    req.key,
                                    alt.get("name", "Unknown"),
                                    alt.get("detail"),
                                    alt.get("url"),
                                    alt.get("distance_meters"),
                                    int(alt.get("satisfies", True)),
                                ),
                            )
                        await db2.commit()
                    finally:
                        await db2.close()
                except Exception:
                    logger.exception(
                        "Fallback failed for listing %d, req %s",
                        listing_row["id"],
                        req.key,
                    )

        fb_tasks = []
        soft_reqs = [r for r in reqs if not r.is_hard]
        for fb_row in fallback_candidates:
            attrs = json.loads(fb_row["attributes"]) if isinstance(fb_row["attributes"], str) else fb_row["attributes"]
            for req in soft_reqs:
                val = attrs.get(req.key)
                if val is None or (req.type == "bool" and val is False):
                    fb_tasks.append(_run_fallback(fb_row, req))

        if fb_tasks:
            await emit_event(
                project_id,
                "phase_change",
                {
                    "phase": "resolving",
                    "message": f"Running {len(fb_tasks)} fallback searches",
                },
            )
            await asyncio.gather(*fb_tasks)

        # --- Phase 5: Scoring ---
        await _set_status(project_id, "scoring")

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT id, attributes FROM listings WHERE project_id = ?",
                (project_id,),
            )
            all_listings = [{"id": r["id"], "attributes": r["attributes"]} for r in await cursor.fetchall()]
        finally:
            await db.close()

        scored = compute_scores(all_listings, reqs)

        db = await get_db()
        try:
            for s in scored:
                await db.execute(
                    "UPDATE listings SET score = ?, hard_pass = ?, data_completeness = ? WHERE id = ?",
                    (s["score"], int(s["hard_pass"]), s["data_completeness"], s["id"]),
                )
            await db.commit()
        finally:
            await db.close()

        await _set_status(project_id, "done")
        await emit_event(project_id, "complete", {"total_listings": len(all_listings)})

    except Exception as e:
        logger.exception("Research failed for project %s", project_id)
        await _set_status(project_id, "error")
        await emit_event(
            project_id,
            "error",
            {
                "message": str(e),
                "traceback": traceback.format_exc(),
            },
        )
