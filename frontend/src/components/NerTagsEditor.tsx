import { ActionIcon, Badge, Group, Select, TextInput } from "@mantine/core";
import { IconPlus, IconX } from "@tabler/icons-react";
import { useState } from "react";

import type { NerTag } from "../api/types";

const ENTITY_TYPES = [
  "PERSON",
  "ORG",
  "LOCATION",
  "DATE",
  "PRODUCT",
  "EVENT",
  "MISC",
];

const TYPE_COLORS: Record<string, string> = {
  PERSON: "blue",
  ORG: "grape",
  LOCATION: "teal",
  DATE: "orange",
  PRODUCT: "cyan",
  EVENT: "pink",
  MISC: "gray",
};

export function NerTagsEditor({
  value,
  onChange,
}: {
  value: NerTag[];
  onChange: (tags: NerTag[]) => void;
}) {
  const [text, setText] = useState("");
  const [type, setType] = useState<string>("PERSON");

  function add() {
    if (!text.trim()) return;
    onChange([...value, { text: text.trim(), type }]);
    setText("");
  }

  function remove(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <div>
      <Group gap={6} mb="xs">
        {value.length === 0 && (
          <Badge variant="light" color="gray">
            none
          </Badge>
        )}
        {value.map((t, i) => (
          <Badge
            key={`${t.text}-${i}`}
            color={TYPE_COLORS[t.type] ?? "gray"}
            variant="light"
            rightSection={
              <ActionIcon
                size="xs"
                variant="transparent"
                color="gray"
                onClick={() => remove(i)}
                aria-label="Remove"
              >
                <IconX size={12} />
              </ActionIcon>
            }
          >
            {t.text} · {t.type}
          </Badge>
        ))}
      </Group>
      <Group gap="xs" wrap="nowrap">
        <TextInput
          flex={1}
          size="xs"
          placeholder="Entity text"
          value={text}
          onChange={(e) => setText(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
        />
        <Select
          size="xs"
          w={120}
          data={ENTITY_TYPES}
          value={type}
          onChange={(v) => setType(v ?? "MISC")}
          allowDeselect={false}
        />
        <ActionIcon variant="light" onClick={add} aria-label="Add entity">
          <IconPlus size={16} />
        </ActionIcon>
      </Group>
    </div>
  );
}
