function inline(text) {
  return text.split(/(\*\*.+?\*\*)/g).map((part, index) => {
    const bold = part.match(/^\*\*(.+?)\*\*$/);
    return bold ? <strong key={index}>{bold[1]}</strong> : part;
  });
}

// Renders AI answers: "**Heading**" lines, "- " bullet lists and inline bold text.
export default function formatInsight(text) {
  const blocks = [];
  for (const [index, line] of text.split("\n").entries()) {
    const heading = line.trim().match(/^\*\*(.+?)\*\*:?$/);
    const bullet = line.match(/^\s*[-•*]\s+(.+)$/);
    if (heading) blocks.push(<h4 className="network-ai-heading" key={index}>{heading[1]}</h4>);
    else if (bullet) {
      const last = blocks.at(-1);
      const item = <li key={index}>{inline(bullet[1])}</li>;
      if (last?.type === "ul") blocks[blocks.length - 1] = <ul className="network-ai-list" key={last.key}>{[...last.props.children, item]}</ul>;
      else blocks.push(<ul className="network-ai-list" key={index}>{[item]}</ul>);
    } else if (line.trim()) blocks.push(<p className="network-ai-line" key={index}>{inline(line)}</p>);
  }
  return blocks;
}
