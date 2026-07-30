import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  List,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  TagsInput,
  Text,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconDeviceFloppy,
  IconSparkles,
  IconThumbDown,
  IconThumbUp,
  IconWorldSearch,
} from "@tabler/icons-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../api/client";
import { createArticle, generateContent, submitFeedback } from "../api/endpoints";
import type { GenerationResponse } from "../api/types";
import { SentimentBadge } from "../components/SentimentBadge";

export function GeneratePage() {
  const navigate = useNavigate();
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const [lastPrompt, setLastPrompt] = useState("");
  const [rated, setRated] = useState<number | null>(null);

  const form = useForm({
    initialValues: {
      prompt: "",
      tone: "professional",
      audience: "",
      length: "medium",
      keywords: [] as string[],
      use_rag: true,
      use_web_search: false,
      research_depth: "deep",
    },
    validate: {
      prompt: (v) => (v.trim().length >= 3 ? null : "Describe what you want to write"),
    },
  });

  const genMutation = useMutation({
    mutationFn: generateContent,
    onSuccess: (data) => {
      setResult(data);
      setRated(null);
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Generation failed") }),
  });

  function rate(value: number) {
    if (!result?.trace_id) return;
    setRated(value);
    submitFeedback({ trace_id: result.trace_id, name: "user_rating", value }).catch(() => {
      /* feedback is best-effort */
    });
    notifications.show({ color: "gray", message: "Thanks for the feedback!" });
  }

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
        sources: c.sources,
        trace_id: result.trace_id,
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
      use_web_search: values.use_web_search,
      research_depth: values.research_depth,
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
                    { value: "short", label: "Short (~500 words)" },
                    { value: "medium", label: "Medium (~1000 words)" },
                    { value: "long", label: "Long (~2000 words)" },
                    { value: "xl", label: "Deep-dive (3000+ words)" },
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
              <Switch
                label="Research the web for real, cited sources"
                description="Searches the live web and grounds the article in what it finds."
                checked={form.values.use_web_search}
                {...form.getInputProps("use_web_search", { type: "checkbox" })}
              />
              {form.values.use_web_search && (
                <SegmentedControl
                  fullWidth
                  data={[
                    { value: "quick", label: "Quick (1 search)" },
                    { value: "deep", label: "Deep (multi-query)" },
                  ]}
                  {...form.getInputProps("research_depth")}
                />
              )}
              <Button
                type="submit"
                leftSection={
                  form.values.use_web_search ? (
                    <IconWorldSearch size={18} />
                  ) : (
                    <IconSparkles size={18} />
                  )
                }
                loading={genMutation.isPending}
              >
                {genMutation.isPending && form.values.use_web_search
                  ? "Researching & writing…"
                  : "Generate"}
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
              {result.research_queries.length > 0 && (
                <Alert
                  icon={<IconWorldSearch size={18} />}
                  color="blue"
                  variant="light"
                  title="Researched the web"
                >
                  <Text size="sm">Ran {result.research_queries.length} search(es):</Text>
                  <List size="xs" mt={4}>
                    {result.research_queries.map((q, i) => (
                      <List.Item key={i}>{q}</List.Item>
                    ))}
                  </List>
                </Alert>
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

              {result.content.sources.length > 0 && (
                <>
                  <Divider label="Sources & references" labelPosition="left" />
                  <List size="sm" spacing={4}>
                    {result.content.sources.map((s, i) => (
                      <List.Item key={`${s.title}-${i}`}>
                        <Badge size="xs" variant="light" mr={6}>
                          {s.type}
                        </Badge>
                        {s.url && !s.url.startsWith("/") ? (
                          <Anchor href={s.url} target="_blank" rel="noopener noreferrer">
                            {s.title}
                          </Anchor>
                        ) : (
                          s.title
                        )}
                      </List.Item>
                    ))}
                  </List>
                </>
              )}

              <Divider />
              <Group justify="space-between">
                {result.trace_id ? (
                  <Group gap={4}>
                    <Text size="xs" c="dimmed" mr={4}>
                      Rate this draft:
                    </Text>
                    <Tooltip label="Good">
                      <ActionIcon
                        variant={rated === 1 ? "filled" : "subtle"}
                        color="teal"
                        onClick={() => rate(1)}
                        aria-label="Thumbs up"
                      >
                        <IconThumbUp size={18} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Poor">
                      <ActionIcon
                        variant={rated === 0 ? "filled" : "subtle"}
                        color="red"
                        onClick={() => rate(0)}
                        aria-label="Thumbs down"
                      >
                        <IconThumbDown size={18} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                ) : (
                  <span />
                )}
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
              </Group>
            </Stack>
          </Card>
        </Grid.Col>
      )}
    </Grid>
  );
}
