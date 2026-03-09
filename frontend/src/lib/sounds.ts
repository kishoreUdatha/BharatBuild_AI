/**
 * Sound notification system for BharatBuild AI
 * Plays sounds when stages are completed during project generation
 */

// Sound URLs - using free notification sounds
const SOUNDS = {
  stageComplete: '/sounds/stage-complete.mp3',
  success: '/sounds/success.mp3',
  error: '/sounds/error.mp3',
  notification: '/sounds/notification.mp3',
}

// Stage-specific messages
export const STAGE_MESSAGES: Record<string, string> = {
  'planning': 'Planning',
  'plan_complete': 'Plan Completed',
  'abstract': 'Abstract',
  'abstract_complete': 'Abstract Completed',
  'writing': 'Writing Code',
  'file_complete': 'File Generated',
  'verification': 'Verifying',
  'verification_complete': 'Verification Completed',
  'fixing': 'Fixing Issues',
  'fix_complete': 'Fix Completed',
  'documentation': 'Generating Docs',
  'docs_complete': 'Documentation Completed',
  'complete': 'Project Completed',
  'error': 'Error Occurred',
}

class SoundManager {
  private enabled: boolean = true
  private volume: number = 0.5
  private audioContext: AudioContext | null = null

  constructor() {
    // Check if user has sound preference stored
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('bharatbuild_sound_enabled')
      this.enabled = stored !== 'false'

      const storedVolume = localStorage.getItem('bharatbuild_sound_volume')
      if (storedVolume) {
        this.volume = parseFloat(storedVolume)
      }
    }
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled
    if (typeof window !== 'undefined') {
      localStorage.setItem('bharatbuild_sound_enabled', String(enabled))
    }
  }

  setVolume(volume: number) {
    this.volume = Math.max(0, Math.min(1, volume))
    if (typeof window !== 'undefined') {
      localStorage.setItem('bharatbuild_sound_volume', String(this.volume))
    }
  }

  isEnabled() {
    return this.enabled
  }

  getVolume() {
    return this.volume
  }

  /**
   * Play a beep sound using Web Audio API (no external files needed)
   */
  private playBeep(frequency: number = 800, duration: number = 150, type: OscillatorType = 'sine') {
    if (!this.enabled || typeof window === 'undefined') return

    try {
      // Create audio context on first use
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      }

      const oscillator = this.audioContext.createOscillator()
      const gainNode = this.audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(this.audioContext.destination)

      oscillator.frequency.value = frequency
      oscillator.type = type

      // Set volume with fade out
      gainNode.gain.setValueAtTime(this.volume * 0.3, this.audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration / 1000)

      oscillator.start(this.audioContext.currentTime)
      oscillator.stop(this.audioContext.currentTime + duration / 1000)
    } catch (e) {
      console.warn('[Sound] Failed to play beep:', e)
    }
  }

  /**
   * Play stage completion sound - pleasant chime
   */
  playStageComplete() {
    // Two-tone chime
    this.playBeep(523, 100, 'sine') // C5
    setTimeout(() => this.playBeep(659, 150, 'sine'), 100) // E5
  }

  /**
   * Play success sound - triumphant chord
   */
  playSuccess() {
    this.playBeep(523, 100, 'sine') // C5
    setTimeout(() => this.playBeep(659, 100, 'sine'), 80) // E5
    setTimeout(() => this.playBeep(784, 200, 'sine'), 160) // G5
  }

  /**
   * Play error sound - descending tone
   */
  playError() {
    this.playBeep(400, 200, 'square')
    setTimeout(() => this.playBeep(300, 300, 'square'), 200)
  }

  /**
   * Play notification sound - single beep
   */
  playNotification() {
    this.playBeep(880, 100, 'sine') // A5
  }

  /**
   * Play file complete sound - quick tick
   */
  playFileComplete() {
    this.playBeep(1200, 50, 'sine')
  }

  /**
   * Play sound based on event type
   */
  playForEvent(eventType: string) {
    if (!this.enabled) return

    switch (eventType) {
      case 'plan_complete':
      case 'abstract_complete':
      case 'verification_complete':
      case 'fix_complete':
      case 'docs_complete':
        this.playStageComplete()
        break
      case 'file_complete':
        this.playFileComplete()
        break
      case 'complete':
        this.playSuccess()
        break
      case 'error':
        this.playError()
        break
      default:
        // Don't play for unknown events
        break
    }
  }
}

// Export singleton instance
export const soundManager = new SoundManager()

// Export helper function
export function playStageSound(stage: string) {
  soundManager.playForEvent(stage)
}
