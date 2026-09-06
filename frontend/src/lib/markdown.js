import { marked } from 'marked';

marked.setOptions({
  gfm: true,
  breaks: true,
});

export function renderMarkdown(content) {
  if (!content) return '';
  try {
    return marked.parse(content);
  } catch (err) {
    console.error('Markdown parse error:', err);
    return content;
  }
}
