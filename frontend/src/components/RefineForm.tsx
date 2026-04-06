import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../api/client'

export function RefineForm({
  projectId,
  onClose,
}: {
  projectId: string
  onClose: () => void
}) {
  const [text, setText] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => api.refineProject(projectId, text),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      onClose()
    },
  })

  return (
    <div className="refine-form">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Add corrections or additional context..."
        rows={2}
        autoFocus
      />
      <div className="refine-actions">
        <button
          onClick={() => mutation.mutate()}
          disabled={!text.trim() || mutation.isPending}
        >
          {mutation.isPending ? 'Refining...' : 'Refine Search'}
        </button>
        <button onClick={onClose} className="btn-secondary">
          Cancel
        </button>
      </div>
    </div>
  )
}
