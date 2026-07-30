import {
  ActionIcon,
  Anchor,
  Badge,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { IconExternalLink, IconPlus, IconTrash } from "@tabler/icons-react";
import { useState } from "react";

import type { Source } from "../api/types";

const SOURCE_TYPES = ["reference", "website", "internal", "dataset", "quote"];

const TYPE_COLORS: Record<string, string> = {
  reference: "blue",
  website: "cyan",
  internal: "violet",
  dataset: "teal",
  quote: "orange",
};

function isInternalLink(url?: string | null): boolean {
  return !!url && url.startsWith("/");
}

export function SourcesEditor({
  value,
  onChange,
}: {
  value: Source[];
  onChange: (sources: Source[]) => void;
}) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("reference");

  function add() {
    if (!title.trim()) return;
    onChange([...value, { title: title.trim(), url: url.trim() || null, type }]);
    setTitle("");
    setUrl("");
  }

  function remove(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <Stack gap="xs">
      {value.length === 0 && (
        <Text size="xs" c="dimmed">
          No sources yet.
        </Text>
      )}
      {value.map((s, i) => (
        <Group
          key={`${s.title}-${i}`}
          justify="space-between"
          wrap="nowrap"
          gap="xs"
        >
          <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
            <Badge color={TYPE_COLORS[s.type] ?? "gray"} variant="light" size="sm">
              {s.type}
            </Badge>
            {s.url && !isInternalLink(s.url) ? (
              <Anchor
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                size="sm"
                lineClamp={1}
              >
                {s.title} <IconExternalLink size={12} />
              </Anchor>
            ) : (
              <Text size="sm" lineClamp={1}>
                {s.title}
              </Text>
            )}
          </Group>
          <ActionIcon
            size="sm"
            variant="subtle"
            color="red"
            onClick={() => remove(i)}
            aria-label="Remove source"
          >
            <IconTrash size={14} />
          </ActionIcon>
        </Group>
      ))}

      <Group gap="xs" wrap="nowrap" align="flex-end">
        <TextInput
          flex={2}
          size="xs"
          label="Title"
          placeholder="Source title"
          value={title}
          onChange={(e) => setTitle(e.currentTarget.value)}
        />
        <Select
          size="xs"
          w={110}
          label="Type"
          data={SOURCE_TYPES}
          value={type}
          onChange={(v) => setType(v ?? "reference")}
          allowDeselect={false}
        />
      </Group>
      <Group gap="xs" wrap="nowrap" align="flex-end">
        <TextInput
          flex={1}
          size="xs"
          label="URL (optional)"
          placeholder="https://…"
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
        />
        <ActionIcon variant="light" onClick={add} aria-label="Add source">
          <IconPlus size={16} />
        </ActionIcon>
      </Group>
    </Stack>
  );
}
