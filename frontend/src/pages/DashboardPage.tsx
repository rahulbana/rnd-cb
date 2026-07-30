import {
  ActionIcon,
  AspectRatio,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Group,
  Image,
  Loader,
  Menu,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconDotsVertical,
  IconFileTypeDocx,
  IconFileTypePdf,
  IconMarkdown,
  IconPlus,
  IconSearch,
  IconTrash,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiErrorMessage, mediaUrl } from "../api/client";
import {
  deleteArticle,
  downloadExport,
  listArticles,
  semanticSearch,
} from "../api/endpoints";
import type { ArticleListItem } from "../api/types";
import { SentimentBadge } from "../components/SentimentBadge";

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");

  const listQuery = useQuery({
    queryKey: ["articles"],
    queryFn: () => listArticles(),
    enabled: activeSearch === "",
  });

  const searchQuery = useQuery({
    queryKey: ["search", activeSearch],
    queryFn: () => semanticSearch(activeSearch),
    enabled: activeSearch !== "",
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => deleteArticle(id),
    onSuccess: () => {
      notifications.show({ message: "Article deleted", color: "gray" });
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      queryClient.invalidateQueries({ queryKey: ["search"] });
    },
    onError: (e) => notifications.show({ color: "red", message: apiErrorMessage(e) }),
  });

  const items: { article: ArticleListItem; score?: number }[] =
    activeSearch !== ""
      ? (searchQuery.data ?? []).map((r) => ({ article: r.article, score: r.score }))
      : (listQuery.data ?? []).map((a) => ({ article: a }));

  const loading = activeSearch !== "" ? searchQuery.isLoading : listQuery.isLoading;

  async function handleExport(id: string, format: string, title: string) {
    try {
      await downloadExport(id, format, title);
    } catch (e) {
      notifications.show({ color: "red", message: apiErrorMessage(e, "Export failed") });
    }
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" wrap="wrap">
        <Title order={2}>My Content</Title>
        <Button leftSection={<IconPlus size={18} />} onClick={() => navigate("/generate")}>
          New Content
        </Button>
      </Group>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setActiveSearch(query.trim());
        }}
      >
        <Group>
          <TextInput
            flex={1}
            placeholder="Semantic search across your library…"
            leftSection={<IconSearch size={16} />}
            value={query}
            onChange={(e) => {
              setQuery(e.currentTarget.value);
              if (e.currentTarget.value === "") setActiveSearch("");
            }}
          />
          <Button type="submit" variant="light">
            Search
          </Button>
        </Group>
      </form>

      {loading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : items.length === 0 ? (
        <Center py="xl">
          <Stack align="center" gap="xs">
            <Text c="dimmed">
              {activeSearch ? "No matches found." : "No content yet."}
            </Text>
            {!activeSearch && (
              <Button variant="light" onClick={() => navigate("/generate")}>
                Generate your first article
              </Button>
            )}
          </Stack>
        </Center>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
          {items.map(({ article, score }) => (
            <Card key={article.id} withBorder shadow="sm" radius="md" padding="md">
              {article.banner_image && (
                <Card.Section
                  mb="xs"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/articles/${article.id}`)}
                >
                  <AspectRatio ratio={3 / 2}>
                    <Image src={mediaUrl(article.banner_image)} alt={article.title} />
                  </AspectRatio>
                </Card.Section>
              )}
              <Group justify="space-between" mb="xs" wrap="nowrap">
                <Badge
                  variant="dot"
                  color={article.status === "published" ? "teal" : "yellow"}
                >
                  {article.status}
                </Badge>
                <Menu withinPortal position="bottom-end">
                  <Menu.Target>
                    <ActionIcon variant="subtle" color="gray">
                      <IconDotsVertical size={18} />
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Label>Export</Menu.Label>
                    <Menu.Item
                      leftSection={<IconFileTypePdf size={16} />}
                      onClick={() => handleExport(article.id, "pdf", article.title)}
                    >
                      PDF
                    </Menu.Item>
                    <Menu.Item
                      leftSection={<IconFileTypeDocx size={16} />}
                      onClick={() => handleExport(article.id, "docx", article.title)}
                    >
                      Word (.docx)
                    </Menu.Item>
                    <Menu.Item
                      leftSection={<IconMarkdown size={16} />}
                      onClick={() => handleExport(article.id, "markdown", article.title)}
                    >
                      Markdown
                    </Menu.Item>
                    <Menu.Divider />
                    <Menu.Item
                      color="red"
                      leftSection={<IconTrash size={16} />}
                      onClick={() => removeMutation.mutate(article.id)}
                    >
                      Delete
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              </Group>

              <Box
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/articles/${article.id}`)}
              >
                <Text fw={600} lineClamp={2} mb={4}>
                  {article.title || "Untitled"}
                </Text>
                <Text size="sm" c="dimmed" lineClamp={3} mih={54}>
                  {article.summary || "No summary yet."}
                </Text>
              </Box>

              <Group justify="space-between" mt="md">
                <SentimentBadge sentiment={article.sentiment} />
                {score !== undefined && (
                  <Badge variant="light" color="violet">
                    {(score * 100).toFixed(0)}% match
                  </Badge>
                )}
              </Group>
              {article.tags.length > 0 && (
                <Group gap={4} mt="xs">
                  {article.tags.slice(0, 3).map((t) => (
                    <Badge key={t} size="xs" variant="outline" color="gray">
                      {t}
                    </Badge>
                  ))}
                </Group>
              )}
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}
