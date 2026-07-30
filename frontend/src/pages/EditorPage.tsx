import {
  ActionIcon,
  AspectRatio,
  Badge,
  Button,
  Card,
  Center,
  Grid,
  Group,
  Image,
  Loader,
  Menu,
  Overlay,
  Paper,
  Select,
  Stack,
  TagsInput,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconDeviceFloppy,
  IconDownload,
  IconFileTypeDocx,
  IconFileTypePdf,
  IconListDetails,
  IconMarkdown,
  IconMessageQuestion,
  IconPhoto,
  IconRefresh,
  IconTextPlus,
  IconWand,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { apiErrorMessage, mediaUrl } from "../api/client";
import {
  downloadExport,
  expandContent,
  generateBanner,
  getArticle,
  updateArticle,
} from "../api/endpoints";
import type { ArticleUpsert, NerTag, Source } from "../api/types";
import { MarkdownEditor } from "../components/RichTextEditor";
import { NerTagsEditor } from "../components/NerTagsEditor";
import { SourcesEditor } from "../components/SourcesEditor";

interface Draft {
  title: string;
  body: string;
  summary: string;
  seo_description: string;
  keywords: string[];
  tags: string[];
  sentiment: string;
  ner_tags: NerTag[];
  sources: Source[];
  status: string;
}

export function EditorPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Draft | null>(null);
  // Banner is managed independently of the editable draft (set via its own
  // endpoint), so it stays out of the unsaved-changes tracking.
  const [banner, setBanner] = useState<string | null>(null);

  const { data: article, isLoading } = useQuery({
    queryKey: ["article", id],
    queryFn: () => getArticle(id),
    enabled: !!id,
  });

  useEffect(() => {
    if (article) {
      setDraft({
        title: article.title,
        body: article.body,
        summary: article.summary,
        seo_description: article.seo_description,
        keywords: article.keywords ?? [],
        tags: article.tags ?? [],
        sentiment: article.sentiment || "neutral",
        ner_tags: article.ner_tags ?? [],
        sources: article.sources ?? [],
        status: article.status || "draft",
      });
      setBanner(article.banner_image);
    }
  }, [article]);

  const bannerMutation = useMutation({
    mutationFn: () => generateBanner(id),
    onSuccess: (updated) => {
      setBanner(updated.banner_image);
      notifications.show({ color: "teal", message: "Banner image generated" });
      queryClient.invalidateQueries({ queryKey: ["articles"] });
    },
    onError: (e) =>
      notifications.show({
        color: "red",
        message: apiErrorMessage(e, "Banner generation failed"),
      }),
  });

  const saveMutation = useMutation({
    mutationFn: (payload: ArticleUpsert) => updateArticle(id, payload),
    onSuccess: () => {
      notifications.show({ color: "teal", message: "Saved" });
      queryClient.invalidateQueries({ queryKey: ["article", id] });
      queryClient.invalidateQueries({ queryKey: ["articles"] });
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Save failed") }),
  });

  const dirty = useMemo(() => {
    if (!article || !draft) return false;
    return (
      JSON.stringify({
        title: article.title,
        body: article.body,
        summary: article.summary,
        seo_description: article.seo_description,
        keywords: article.keywords ?? [],
        tags: article.tags ?? [],
        sentiment: article.sentiment,
        ner_tags: article.ner_tags ?? [],
        sources: article.sources ?? [],
        status: article.status,
      }) !== JSON.stringify(draft)
    );
  }, [article, draft]);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
  }

  const wordCount = useMemo(
    () => (draft?.body?.trim() ? draft.body.trim().split(/\s+/).length : 0),
    [draft?.body]
  );

  const expandMutation = useMutation({
    mutationFn: (mode: string) =>
      expandContent({ title: draft?.title ?? "", body: draft?.body ?? "", mode }),
    onSuccess: (data) => {
      set("body", data.body);
      notifications.show({ color: "teal", message: "Content expanded — review & save" });
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Expand failed") }),
  });

  async function handleExport(format: string) {
    try {
      await downloadExport(id, format, draft?.title ?? "article");
    } catch (e) {
      notifications.show({ color: "red", message: apiErrorMessage(e, "Export failed") });
    }
  }

  if (isLoading || !draft) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap">
        <Group>
          <ActionIcon variant="subtle" onClick={() => navigate("/")} aria-label="Back">
            <IconArrowLeft size={20} />
          </ActionIcon>
          <Title order={3}>Edit article</Title>
          {dirty && (
            <Badge color="yellow" variant="light">
              Unsaved changes
            </Badge>
          )}
        </Group>
        <Group>
          <Menu>
            <Menu.Target>
              <Button variant="default" leftSection={<IconDownload size={18} />}>
                Export
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<IconFileTypePdf size={16} />}
                onClick={() => handleExport("pdf")}
              >
                PDF
              </Menu.Item>
              <Menu.Item
                leftSection={<IconFileTypeDocx size={16} />}
                onClick={() => handleExport("docx")}
              >
                Word (.docx)
              </Menu.Item>
              <Menu.Item
                leftSection={<IconMarkdown size={16} />}
                onClick={() => handleExport("markdown")}
              >
                Markdown
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
          <Button
            leftSection={<IconDeviceFloppy size={18} />}
            loading={saveMutation.isPending}
            disabled={!dirty}
            onClick={() => saveMutation.mutate(draft)}
          >
            Save
          </Button>
        </Group>
      </Group>

      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Stack>
            {/* Banner image */}
            {banner ? (
              <Card withBorder radius="md" p={0} pos="relative">
                <AspectRatio ratio={3 / 2}>
                  <Image src={mediaUrl(banner)} alt={draft.title} />
                </AspectRatio>
                {bannerMutation.isPending && (
                  <Overlay color="#000" backgroundOpacity={0.5} center>
                    <Loader color="white" />
                  </Overlay>
                )}
                <Button
                  size="xs"
                  variant="white"
                  color="dark"
                  leftSection={<IconRefresh size={14} />}
                  onClick={() => bannerMutation.mutate()}
                  loading={bannerMutation.isPending}
                  style={{ position: "absolute", top: 10, right: 10 }}
                >
                  Regenerate
                </Button>
              </Card>
            ) : (
              <Card withBorder radius="md" py="xl">
                <Stack align="center" gap="xs">
                  <IconPhoto size={32} color="var(--mantine-color-dimmed)" />
                  <Text size="sm" c="dimmed" ta="center">
                    Add a title-aware banner image to the top of this article.
                  </Text>
                  <Button
                    variant="light"
                    leftSection={<IconPhoto size={16} />}
                    onClick={() => bannerMutation.mutate()}
                    loading={bannerMutation.isPending}
                  >
                    Generate banner image
                  </Button>
                </Stack>
              </Card>
            )}

            <TextInput
              size="lg"
              placeholder="Article title"
              value={draft.title}
              onChange={(e) => set("title", e.currentTarget.value)}
              styles={{ input: { fontWeight: 700, fontSize: 22 } }}
            />
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {wordCount} words
              </Text>
              <Menu position="bottom-end">
                <Menu.Target>
                  <Button
                    variant="light"
                    size="xs"
                    leftSection={<IconWand size={16} />}
                    loading={expandMutation.isPending}
                  >
                    Expand with AI
                  </Button>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>Make it longer / richer</Menu.Label>
                  <Menu.Item
                    leftSection={<IconTextPlus size={16} />}
                    onClick={() => expandMutation.mutate("longer")}
                  >
                    Expand &amp; lengthen (~2×)
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconListDetails size={16} />}
                    onClick={() => expandMutation.mutate("examples")}
                  >
                    Add examples &amp; detail
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconWand size={16} />}
                    onClick={() => expandMutation.mutate("depth")}
                  >
                    Deepen existing sections
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconMessageQuestion size={16} />}
                    onClick={() => expandMutation.mutate("faq")}
                  >
                    Append an FAQ section
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
            <MarkdownEditor value={draft.body} onChange={(md) => set("body", md)} />
          </Stack>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Stack>
            <Paper withBorder p="md" radius="md">
              <Text fw={600} mb="sm">
                Publishing
              </Text>
              <Select
                label="Status"
                data={["draft", "published"]}
                value={draft.status}
                onChange={(v) => set("status", v ?? "draft")}
                allowDeselect={false}
              />
            </Paper>

            <Paper withBorder p="md" radius="md">
              <Text fw={600} mb="sm">
                Summary
              </Text>
              <Textarea
                autosize
                minRows={3}
                value={draft.summary}
                onChange={(e) => set("summary", e.currentTarget.value)}
              />
            </Paper>

            <Card withBorder p="md" radius="md">
              <Text fw={600} mb="sm">
                SEO
              </Text>
              <Stack gap="sm">
                <Textarea
                  label="Meta description"
                  autosize
                  minRows={2}
                  value={draft.seo_description}
                  onChange={(e) => set("seo_description", e.currentTarget.value)}
                />
                <TagsInput
                  label="Keywords"
                  value={draft.keywords}
                  onChange={(v) => set("keywords", v)}
                />
              </Stack>
            </Card>

            <Paper withBorder p="md" radius="md">
              <Text fw={600} mb="sm">
                Classification
              </Text>
              <Stack gap="sm">
                <Select
                  label="Sentiment"
                  data={["positive", "neutral", "negative"]}
                  value={draft.sentiment}
                  onChange={(v) => set("sentiment", v ?? "neutral")}
                  allowDeselect={false}
                />
                <TagsInput
                  label="Tags"
                  value={draft.tags}
                  onChange={(v) => set("tags", v)}
                />
                <div>
                  <Text size="sm" fw={500} mb={4}>
                    Named entities (NER)
                  </Text>
                  <NerTagsEditor
                    value={draft.ner_tags}
                    onChange={(v) => set("ner_tags", v)}
                  />
                </div>
              </Stack>
            </Paper>

            <Paper withBorder p="md" radius="md">
              <Text fw={600} mb="sm">
                Sources &amp; references
              </Text>
              <SourcesEditor value={draft.sources} onChange={(v) => set("sources", v)} />
            </Paper>
          </Stack>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
