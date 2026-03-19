import axios from 'axios'

const BASE = ''  // proxied by Vite dev server to http://localhost:8000

export interface AttributeSchema {
  name: string
  type: string
  primary_key: boolean
  nullable: boolean
  description: string
  enum: string[]
}

export interface RelationshipSchema {
  to: string
  via: string
  cardinality: string
  type: string | null
}

export interface EntitySchema {
  name: string
  snake_name: string
  description: string
  attributes: AttributeSchema[]
  relationships: RelationshipSchema[]
}

export interface ModelSchema {
  name: string
  version: string
  description: string
  entity_count: number
  entities: EntitySchema[]
}

export interface ValidationResult {
  valid: boolean
  message: string
  errors: string[]
}

export interface GenerateOptions {
  source_name?: string
  seed_rows?: number
  seed?: number | null
  include_seeds?: boolean
}

export interface SeedPreviewRow {
  entity_name: string
  columns: string[]
  rows: (string | null)[][]
}

export interface GeneratePreviewResult {
  files: Record<string, string>
}

export const api = {
  async uploadModel(file: File): Promise<ModelSchema> {
    const form = new FormData()
    form.append('file', file)
    const res = await axios.post<ModelSchema>(`${BASE}/model/upload`, form)
    return res.data
  },

  async validateModel(file: File): Promise<ValidationResult> {
    const form = new FormData()
    form.append('file', file)
    const res = await axios.post<ValidationResult>(`${BASE}/model/validate`, form)
    return res.data
  },

  async getEntities(): Promise<ModelSchema> {
    const res = await axios.get<ModelSchema>(`${BASE}/model/entities`)
    return res.data
  },

  async generatePreview(opts: GenerateOptions = {}): Promise<GeneratePreviewResult> {
    const res = await axios.post<GeneratePreviewResult>(`${BASE}/generate/preview`, opts)
    return res.data
  },

  async downloadProject(opts: GenerateOptions = {}): Promise<Blob> {
    const res = await axios.post(`${BASE}/generate/download`, opts, { responseType: 'blob' })
    return res.data
  },

  async seedPreview(opts: GenerateOptions = {}): Promise<SeedPreviewRow[]> {
    const res = await axios.post<SeedPreviewRow[]>(`${BASE}/seed/preview`, opts)
    return res.data
  },
}
