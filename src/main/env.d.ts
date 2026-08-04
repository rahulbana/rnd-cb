// Allow importing raw text assets (e.g. SQL) in the main process bundle.
declare module '*.sql?raw' {
  const content: string
  export default content
}
