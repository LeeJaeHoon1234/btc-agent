import { defineConfig } from 'vite'

const repository = process.env.GITHUB_REPOSITORY?.split('/')[1]
const defaultBase = repository ? `/${repository}/` : '/'

export default defineConfig({
  base: process.env.VITE_BASE || defaultBase,
})
