export type JarvisState = 'Idle' | 'Listening' | 'Transcribing' | 'Thinking' | 'Speaking' | 'Error' | 'Disabled' | string

export interface RuntimeState {
  assistantState: JarvisState
  transcript: string
  response: string
  responseLanguage: string
  spoken: string
  logs: string[]
  error: string
}

export interface ConfigState {
  ai_provider?: string
  ai_model_name?: string
  language_mode?: string
  mic_name?: string
  voice_enabled?: boolean
  wake_word_enabled?: boolean
  wake_word_threshold?: number
  tone_mode?: string
  address_name?: string
  verbosity_mode?: string
  searxng_base_url?: string
  conversation_mode_enabled?: boolean
  [key: string]: unknown
}

export interface Snapshot {
  version: number
  runtime: RuntimeState
  config: ConfigState
  aiStatus: string
  capabilities: string[]
}

export interface Metrics {
  cpu: number
  ram: number
  battery: number | null
}
