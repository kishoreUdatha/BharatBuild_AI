import { useCallback } from 'react'
import { useTerminalStore } from '@/store/terminalStore'

export const useTerminal = () => {
  const {
    logs,
    isVisible,
    height,
    activeTab,
    isExecuting,
    sessionActive,
    addLog,
    clearLogs,
    setVisible,
    setHeight,
    setActiveTab,
    executeCommand,
    startSession,
    endSession
  } = useTerminalStore()

  const toggleTerminal = useCallback(() => {
    console.log('[useTerminal] toggleTerminal called, current isVisible:', isVisible)
    setVisible(!isVisible)
  }, [isVisible, setVisible])

  // Open terminal explicitly (avoids race conditions with toggle)
  const openTerminal = useCallback(() => {
    console.log('[useTerminal] openTerminal called')
    setVisible(true)
  }, [setVisible])

  // Close terminal explicitly
  const closeTerminal = useCallback(() => {
    console.log('[useTerminal] closeTerminal called')
    setVisible(false)
  }, [setVisible])

  // Run command in container (real execution)
  const runCommand = useCallback(async (command: string) => {
    await executeCommand(command)
  }, [executeCommand])

  const increaseHeight = useCallback(() => {
    setHeight(height + 50)
  }, [height, setHeight])

  const decreaseHeight = useCallback(() => {
    setHeight(height - 50)
  }, [height, setHeight])

  return {
    logs,
    isVisible,
    height,
    activeTab,
    isExecuting,
    sessionActive,
    addLog,
    clearLogs,
    toggleTerminal,
    openTerminal,
    closeTerminal,
    setHeight,
    setActiveTab,
    runCommand,
    increaseHeight,
    decreaseHeight,
    startSession,
    endSession
  }
}
