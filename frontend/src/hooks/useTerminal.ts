import { useCallback } from 'react'
import { useTerminalStore } from '@/store/terminalStore'

export const useTerminal = () => {
  const {
    logs,
    isVisible,
    height,
    activeTab,
    addLog,
    clearLogs,
    setVisible,
    setHeight,
    setActiveTab,
    executeCommand
  } = useTerminalStore()

  const toggleTerminal = useCallback(() => {
    setVisible(!isVisible)
  }, [isVisible, setVisible])

  const runCommand = useCallback(async (command: string) => {
    executeCommand(command)
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
    addLog,
    clearLogs,
    toggleTerminal,
    setHeight,
    setActiveTab,
    runCommand,
    increaseHeight,
    decreaseHeight
  }
}
