import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'
import { spawn, type ChildProcess } from 'child_process'
import { config as loadEnv } from 'dotenv'

loadEnv()

const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1'
const BACKEND_PORT = process.env.BACKEND_PORT || '8000'
// If BACKEND_URL is provided, we connect to an already-running backend (dev)
// instead of spawning our own.
const EXTERNAL_BACKEND = Boolean(process.env.BACKEND_URL)
const BACKEND_URL = process.env.BACKEND_URL || `http://${BACKEND_HOST}:${BACKEND_PORT}`

let mainWindow: BrowserWindow | null = null
let backend: ChildProcess | null = null

function resolveBackendDir(): string {
  const candidates = [
    process.env.BACKEND_DIR,
    join(__dirname, '../../../backend'), // dev: frontend/out/main -> repo/backend
    join(process.resourcesPath || '', 'backend'), // packaged
    join(app.getAppPath(), 'backend')
  ].filter(Boolean) as string[]
  return candidates.find((c) => existsSync(join(c, 'app', 'main.py'))) || candidates[1]
}

function startBackend(): void {
  if (EXTERNAL_BACKEND) {
    console.log(`[backend] Using external backend at ${BACKEND_URL}`)
    return
  }
  const cwd = resolveBackendDir()
  const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
  console.log(`[backend] Spawning: ${python} -m uvicorn (cwd=${cwd}, port=${BACKEND_PORT})`)

  backend = spawn(
    python,
    ['-m', 'uvicorn', 'app.main:app', '--host', BACKEND_HOST, '--port', BACKEND_PORT],
    { cwd, env: { ...process.env }, stdio: 'inherit' }
  )
  backend.on('error', (err) => console.error('[backend] Failed to start:', err.message))
  backend.on('exit', (code) => console.log(`[backend] Exited with code ${code}`))
}

async function waitForBackend(timeoutMs = 30_000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`)
      if (res.ok) return true
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 350))
  }
  return false
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    show: false,
    title: 'RND CB — AI Coding Agent',
    backgroundColor: '#1e1e2e',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [`--backend-url=${BACKEND_URL}`]
    }
  })

  mainWindow.on('ready-to-show', () => mainWindow?.show())
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  const devUrl = process.env['ELECTRON_RENDERER_URL']
  if (devUrl) {
    void mainWindow.loadURL(devUrl)
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

ipcMain.handle('dialog:chooseDirectory', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, { properties: ['openDirectory'] })
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

app.whenReady().then(async () => {
  startBackend()
  const ready = await waitForBackend()
  if (!ready) {
    dialog.showErrorBox(
      'Backend not reachable',
      `The FastAPI backend did not start at ${BACKEND_URL}.\n\n` +
        'Ensure Python dependencies are installed (pip install -r backend/requirements.txt) ' +
        'or set BACKEND_URL to a running backend.'
    )
  }
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (backend && !backend.killed) backend.kill()
})
