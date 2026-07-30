import { RichTextEditor, Link } from "@mantine/tiptap";
import { useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";
import { useEffect } from "react";

interface Props {
  /** Markdown content. */
  value: string;
  onChange: (markdown: string) => void;
  minHeight?: number;
}

/**
 * WYSIWYG editor that reads and writes Markdown, so the content stays
 * consistent with the backend (which stores and exports Markdown).
 */
export function MarkdownEditor({ value, onChange, minHeight = 360 }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Link,
      Markdown.configure({ html: false, linkify: true, transformPastedText: true }),
    ],
    content: value,
    onUpdate: ({ editor }) => {
      const md = editor.storage.markdown.getMarkdown();
      onChange(md);
    },
  });

  // Sync external value changes (e.g. after AI generation) into the editor
  // without clobbering the caret while the user is actively typing.
  useEffect(() => {
    if (!editor) return;
    const current = editor.storage.markdown.getMarkdown();
    if (value !== current && !editor.isFocused) {
      editor.commands.setContent(value, false);
    }
  }, [value, editor]);

  return (
    <RichTextEditor editor={editor}>
      <RichTextEditor.Toolbar sticky stickyOffset={60}>
        <RichTextEditor.ControlsGroup>
          <RichTextEditor.Bold />
          <RichTextEditor.Italic />
          <RichTextEditor.Strikethrough />
          <RichTextEditor.Code />
        </RichTextEditor.ControlsGroup>
        <RichTextEditor.ControlsGroup>
          <RichTextEditor.H1 />
          <RichTextEditor.H2 />
          <RichTextEditor.H3 />
        </RichTextEditor.ControlsGroup>
        <RichTextEditor.ControlsGroup>
          <RichTextEditor.BulletList />
          <RichTextEditor.OrderedList />
          <RichTextEditor.Blockquote />
          <RichTextEditor.CodeBlock />
        </RichTextEditor.ControlsGroup>
        <RichTextEditor.ControlsGroup>
          <RichTextEditor.Link />
          <RichTextEditor.Unlink />
        </RichTextEditor.ControlsGroup>
        <RichTextEditor.ControlsGroup>
          <RichTextEditor.Undo />
          <RichTextEditor.Redo />
        </RichTextEditor.ControlsGroup>
      </RichTextEditor.Toolbar>
      <RichTextEditor.Content style={{ minHeight }} />
    </RichTextEditor>
  );
}
