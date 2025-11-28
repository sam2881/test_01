'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Modal } from '../ui/Modal'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { Button } from '../ui/Button'
import { api } from '@/lib/api'
import { INCIDENT_PRIORITIES } from '@/lib/constants'
import type { CreateIncidentRequest } from '@/types/incident'

interface CreateIncidentModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function CreateIncidentModal({ isOpen, onClose, onSuccess }: CreateIncidentModalProps) {
  const [formData, setFormData] = useState<CreateIncidentRequest>({
    short_description: '',
    description: '',
    priority: 'P3',
    category: '',
    affected_service: '',
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateIncidentRequest) => api.createIncident(data),
    onSuccess: () => {
      toast.success('Incident created successfully')
      onSuccess()
      setFormData({
        short_description: '',
        description: '',
        priority: 'P3',
        category: '',
        affected_service: '',
      })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to create incident')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.short_description || !formData.description) {
      toast.error('Please fill in all required fields')
      return
    }
    createMutation.mutate(formData)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Incident"
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Short Description *"
          placeholder="Brief description of the incident"
          value={formData.short_description}
          onChange={(e) =>
            setFormData({ ...formData, short_description: e.target.value })
          }
          required
        />

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Description *
          </label>
          <textarea
            className="flex min-h-[120px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            placeholder="Detailed description of the incident"
            value={formData.description}
            onChange={(e) =>
              setFormData({ ...formData, description: e.target.value })
            }
            required
          />
        </div>

        <Select
          label="Priority"
          options={INCIDENT_PRIORITIES.map((p) => ({ value: p, label: p }))}
          value={formData.priority || 'P3'}
          onChange={(e) =>
            setFormData({ ...formData, priority: e.target.value as any })
          }
        />

        <Input
          label="Category"
          placeholder="e.g., Performance, Security, Network"
          value={formData.category}
          onChange={(e) =>
            setFormData({ ...formData, category: e.target.value })
          }
        />

        <Input
          label="Affected Service"
          placeholder="e.g., api-gateway, user-service"
          value={formData.affected_service}
          onChange={(e) =>
            setFormData({ ...formData, affected_service: e.target.value })
          }
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={createMutation.isPending}>
            Create Incident
          </Button>
        </div>
      </form>
    </Modal>
  )
}
