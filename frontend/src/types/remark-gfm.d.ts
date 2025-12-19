declare module 'remark-gfm' {
  import { Plugin } from 'unified'

  interface RemarkGfmOptions {
    singleTilde?: boolean
    tableCellPadding?: boolean
    tablePipeAlign?: boolean
    stringLength?: (value: string) => number
  }

  const remarkGfm: Plugin<[RemarkGfmOptions?]>
  export default remarkGfm
}
