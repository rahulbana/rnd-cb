import {
  Anchor,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconSparkles } from "@tabler/icons-react";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : "Invalid email"),
      password: (v) => (v.length >= 1 ? null : "Password required"),
    },
  });

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(values: typeof form.values) {
    setError(null);
    setLoading(true);
    try {
      await login(values.email, values.password);
      navigate("/");
    } catch (e) {
      setError(apiErrorMessage(e, "Login failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Center h="100vh" p="md">
      <Paper withBorder shadow="md" p="xl" radius="lg" w={420} maw="100%">
        <Stack align="center" mb="lg">
          <IconSparkles size={36} color="var(--mantine-color-violet-6)" />
          <Title order={2}>Welcome back</Title>
          <Text c="dimmed" size="sm">
            Sign in to your content workspace
          </Text>
        </Stack>
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Email"
              placeholder="you@example.com"
              {...form.getInputProps("email")}
            />
            <PasswordInput
              label="Password"
              placeholder="Your password"
              {...form.getInputProps("password")}
            />
            {error && (
              <Text c="red" size="sm">
                {error}
              </Text>
            )}
            <Button type="submit" fullWidth loading={loading}>
              Sign in
            </Button>
            <Text size="sm" ta="center" c="dimmed">
              No account?{" "}
              <Anchor component={Link} to="/register">
                Create one
              </Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}
