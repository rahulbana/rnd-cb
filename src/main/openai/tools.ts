import type OpenAI from 'openai'
import { listFiles, readFile, writeFile } from '../tools/fileTools'
import { runCommand } from '../tools/shellTools'

// Tools whose execution changes state on disk / runs code. These are gated by
// the approval flow when permission mode is "ask".
export const SIDE_EFFECTING_TOOLS = new Set(['write_file', 'run_command'])

export const toolDefinitions: OpenAI.Chat.Completions.ChatCompletionTool[] = [
  {
    type: 'function',
    function: {
      name: 'list_files',
      description:
        'List files and directories within the project. Returns paths relative to the project root. Common build/vendor dirs are skipped.',
      parameters: {
        type: 'object',
        properties: {
          dir: { type: 'string', description: 'Subdirectory to list, relative to project root. Defaults to the whole project.' }
        }
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'read_file',
      description: 'Read the contents of a text file within the project.',
      parameters: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'File path relative to the project root.' }
        },
        required: ['path']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'write_file',
      description:
        'Create or overwrite a text file within the project with the given full content. Parent directories are created as needed.',
      parameters: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'File path relative to the project root.' },
          content: { type: 'string', description: 'The complete new content of the file.' }
        },
        required: ['path', 'content']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'run_command',
      description:
        'Run a shell command from the project root and return its combined stdout/stderr and exit code. Use for building, testing, git, installing dependencies, etc.',
      parameters: {
        type: 'object',
        properties: {
          command: { type: 'string', description: 'The shell command to execute.' }
        },
        required: ['command']
      }
    }
  }
]

export interface ParsedToolCall {
  name: string
  args: Record<string, unknown>
}

export function summarizeToolCall(name: string, args: Record<string, unknown>): { summary: string; details: string } {
  switch (name) {
    case 'write_file':
      return {
        summary: `Write file: ${args.path}`,
        details: typeof args.content === 'string' ? (args.content as string).slice(0, 2000) : ''
      }
    case 'run_command':
      return { summary: `Run command: ${args.command}`, details: String(args.command ?? '') }
    default:
      return { summary: name, details: JSON.stringify(args) }
  }
}

/** Execute a tool call and return a string result for the model. */
export async function executeTool(root: string, name: string, args: Record<string, unknown>): Promise<string> {
  switch (name) {
    case 'list_files':
      return listFiles(root, typeof args.dir === 'string' ? args.dir : '.')
    case 'read_file':
      return readFile(root, String(args.path))
    case 'write_file':
      return writeFile(root, String(args.path), String(args.content ?? ''))
    case 'run_command': {
      const res = await runCommand(root, String(args.command))
      return `Exit code: ${res.exitCode}\n\n${res.output}`
    }
    default:
      throw new Error(`Unknown tool: ${name}`)
  }
}
