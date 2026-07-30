import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Center,
  FileButton,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconFile,
  IconInfoCircle,
  IconLink,
  IconSettings,
  IconTrash,
  IconUpload,
  IconWriting,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiErrorMessage } from "../api/client";
import {
  addStyleLink,
  deleteStyleRef,
  listStyleRefs,
  uploadStyleFile,
} from "../api/endpoints";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");

  const refsQuery = useQuery({
    queryKey: ["style-refs"],
    queryFn: listStyleRefs,
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["style-refs"] });
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadStyleFile(file),
    onSuccess: (ref) => {
      notifications.show({ color: "teal", message: `Added “${ref.name}”` });
      invalidate();
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Upload failed") }),
  });

  const linkMutation = useMutation({
    mutationFn: (u: string) => addStyleLink(u),
    onSuccess: (ref) => {
      notifications.show({ color: "teal", message: `Added “${ref.name}”` });
      setUrl("");
      invalidate();
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e, "Could not add link") }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteStyleRef(id),
    onSuccess: () => {
      notifications.show({ color: "gray", message: "Removed" });
      invalidate();
    },
    onError: (e) =>
      notifications.show({ color: "red", message: apiErrorMessage(e) }),
  });

  const refs = refsQuery.data ?? [];

  return (
    <Stack gap="lg" maw={820}>
      <div>
        <Group gap="xs">
          <IconSettings size={24} />
          <Title order={2}>Settings</Title>
        </Group>
        <Text c="dimmed" size="sm" mt={4}>
          Manage your workspace preferences.
        </Text>
      </div>

      <Paper withBorder radius="md" p="lg">
        <Group gap="xs" mb="xs">
          <IconWriting size={22} color="var(--mantine-color-violet-6)" />
          <Title order={4}>Writing style references</Title>
        </Group>
        <Text c="dimmed" size="sm" mb="md">
          Add links or upload samples of your previous writing. The AI studies
          these to match your voice, tone and style when generating new content.
        </Text>

        <Alert
          icon={<IconInfoCircle size={16} />}
          color="violet"
          variant="light"
          mb="lg"
        >
          Supported files: <b>.txt</b>, <b>.md</b>, <b>.docx</b> (max 10&nbsp;MB).
          The most relevant samples are automatically used on each generation.
        </Alert>

        {/* Add by link */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (url.trim()) linkMutation.mutate(url.trim());
          }}
        >
          <Group align="flex-end" mb="md" wrap="nowrap">
            <TextInput
              flex={1}
              label="Add from a link"
              placeholder="https://your-blog.com/an-article"
              leftSection={<IconLink size={16} />}
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
            />
            <Button type="submit" loading={linkMutation.isPending}>
              Add link
            </Button>
          </Group>
        </form>

        {/* Upload file */}
        <Group mb="lg">
          <FileButton
            onChange={(file) => file && uploadMutation.mutate(file)}
            accept=".txt,.md,.docx,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          >
            {(props) => (
              <Button
                {...props}
                variant="light"
                leftSection={<IconUpload size={16} />}
                loading={uploadMutation.isPending}
              >
                Upload a file
              </Button>
            )}
          </FileButton>
          <Text size="xs" c="dimmed">
            .txt, .md or .docx
          </Text>
        </Group>

        {/* Existing references */}
        <Title order={6} mb="xs">
          Your references {refs.length > 0 && `(${refs.length})`}
        </Title>
        {refsQuery.isLoading ? (
          <Center py="md">
            <Loader size="sm" />
          </Center>
        ) : refs.length === 0 ? (
          <Text c="dimmed" size="sm">
            No references yet. Add a link or upload a file above.
          </Text>
        ) : (
          <Stack gap="xs">
            {refs.map((ref) => (
              <Card key={ref.id} withBorder radius="md" padding="sm">
                <Group justify="space-between" wrap="nowrap">
                  <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
                    {ref.source_type === "link" ? (
                      <IconLink size={18} />
                    ) : (
                      <IconFile size={18} />
                    )}
                    <div style={{ minWidth: 0 }}>
                      <Text size="sm" fw={500} lineClamp={1}>
                        {ref.name}
                      </Text>
                      <Text size="xs" c="dimmed" lineClamp={1}>
                        {ref.origin}
                      </Text>
                    </div>
                  </Group>
                  <Group gap="xs" wrap="nowrap">
                    <Badge variant="light" color="gray">
                      {(ref.char_count / 1000).toFixed(1)}k chars
                    </Badge>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      onClick={() => deleteMutation.mutate(ref.id)}
                      aria-label="Delete reference"
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Group>
              </Card>
            ))}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
}
