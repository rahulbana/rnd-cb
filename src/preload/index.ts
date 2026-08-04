import { contextBridge, ipcRenderer } from 'electron'

// Extract the backend URL passed by the main process via additionalArguments.
function backendUrl(): string {
  const arg = process.argv.find((a) => a.startsWith('--backend-url='))
  return arg ? arg.slice('--backend-url='.length) : 'http://127.0.0.1:8000'
}

export interface DesktopBridge {
  backendUrl: string
  chooseDirectory(): Promise<string | null>
}

const desktop: DesktopBridge = {
  backendUrl: backendUrl(),
  chooseDirectory: () => ipcRenderer.invoke('dialog:chooseDirectory') as Promise<string | null>
}

contextBridge.exposeInMainWorld('desktop', desktop)
