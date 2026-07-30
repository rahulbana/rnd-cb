import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Paper,
  Select,
  Stack,
  Switch,
  TagsInput,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconDeviceFloppy, IconSparkles } from "@tabler/icons-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../api/client";
import { createArticle, generateContent } from "../api/endpoints";
import type { GenerationResponse } from "../api/types";
import { SentimentBadge } from "../components/SentimentBadge";

export function GeneratePage() {
  const navigate = useNavigate();
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const [lastPrompt, setLastPrompt] = useState("");

  const form = useForm({
    initialValues: {
      prompt: "",
      tone: "professional",
      audience: "",
      length: "medium",
      keywords: [] as string[],
      use_rag: true,
    },
    validate: {
      prompt: (v) => (v.trim().length >= 3 ? null : "Describe what you want to write"),
    },
  });

  const genMutation = useMutation({
    mutationFn: generateContent,
    onSuccess: (data) => setResult(data),
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Generation failed") }),
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!result) throw new Error("Nothing to save");
      const c = result.content;
      return createArticle({
        prompt: lastPrompt,
        title: c.title,
        body: c.body,
        summary: c.summary,
        seo_description: c.seo_description,
        keywords: c.keywords,
        sentiment: c.sentiment,
        tags: c.tags,
        ner_tags: c.ner_tags,
        status: "draft",
      });
    },
    onSuccess: (article) => {
      notifications.show({ color: "teal", message: "Draft saved" });
      navigate(`/articles/${article.id}`);
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Save failed") }),
  });

  function handleGenerate(values: typeof form.values) {
    setLastPrompt(values.prompt);
    genMutation.mutate({
      prompt: values.prompt,
      tone: values.tone,
      audience: values.audience || undefined,
      length: values.length,
      keywords: values.keywords,
      use_rag: values.use_rag,
    });
  }

  return (
    <Grid gutter="lg">
      <Grid.Col span={{ base: 12, md: result ? 5 : 12 }}>
        <Paper withBorder p="lg" radius="md">
          <Group mb="md">
            <IconSparkles size={22} color="var(--mantine-color-violet-6)" />
            <Title order={3}>Generate content</Title>
          </Group>
          <form onSubmit={form.onSubmit(handleGenerate)}>
            <Stack>
              <Textarea
                label="What do you want to write about?"
                placeholder="e.g. A beginner-friendly guide to vector databases for RAG applications"
                minRows={4}
                autosize
                {...form.getInputProps("prompt")}
              />
              <Group grow>
                <Select
                  label="Tone"
                  data={["professional", "casual", "witty", "authoritative", "friendly"]}
                  {...form.getInputProps("tone")}
                />
                <Select
                  label="Length"
                  data={[
                    { value: "short", label: "Short (~300 words)" },
                    { value: "medium", label: "Medium (~800 words)" },
                    { value: "long", label: "Long (~1500 words)" },
                  ]}
                  {...form.getInputProps("length")}
                />
              </Group>
              <Textarea
                label="Target audience (optional)"
                placeholder="e.g. software engineers new to AI"
                autosize
                minRows={1}
                {...form.getInputProps("audience")}
              />
              <TagsInput
                label="SEO keywords (optional)"
                placeholder="Type and press Enter"
                {...form.getInputProps("keywords")}
              />
              <Switch
                label="Use my past articles for style consistency (RAG)"
                checked={form.values.use_rag}
                {...form.getInputProps("use_rag", { type: "checkbox" })}
              />
              <Button
                type="submit"
                leftSection={<IconSparkles size={18} />}
                loading={genMutation.isPending}
              >
                Generate
              </Button>
            </Stack>
          </form>
        </Paper>
      </Grid.Col>

      {result && (
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder radius="md" padding="lg">
            <Stack>
              {result.possible_duplicates.length > 0 && (
                <Alert
                  icon={<IconAlertTriangle size={18} />}
                  color="yellow"
                  title="Possible duplicate content"
                >
                  Similar to:{" "}
                  {result.possible_duplicates.map((d) => d.title).join(", ")}
                </Alert>
              )}
              {result.context_used.length > 0 && (
                <Text size="xs" c="dimmed">
                  Used {result.context_used.length} past article(s) as style context.
                </Text>
              )}

              <Title order={3}>{result.content.title}</Title>
              <Group>
                <SentimentBadge sentiment={result.content.sentiment} />
                {result.content.tags.map((t) => (
                  <Badge key={t} variant="light" color="grape">
                    {t}
                  </Badge>
                ))}
              </Group>
              <Text c="dimmed" fs="italic">
                {result.content.summary}
              </Text>
              <Divider />
              <Text
                size="sm"
                style={{ whiteSpace: "pre-wrap", maxHeight: 320, overflow: "auto" }}
              >
                {result.content.body}
              </Text>
              <Divider />
              <Group justify="flex-end">
                <Button variant="default" onClick={() => setResult(null)}>
                  Discard
                </Button>
                <Button
                  leftSection={<IconDeviceFloppy size={18} />}
                  loading={saveMutation.isPending}
                  onClick={() => saveMutation.mutate()}
                >
                  Save draft & edit
                </Button>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>
      )}
    </Grid>
  );
}
