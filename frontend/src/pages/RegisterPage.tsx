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

export function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm({
    initialValues: { full_name: "", email: "", password: "" },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : "Invalid email"),
      password: (v) => (v.length >= 8 ? null : "At least 8 characters"),
    },
  });

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(values: typeof form.values) {
    setError(null);
    setLoading(true);
    try {
      await register(values.email, values.password, values.full_name || undefined);
      navigate("/");
    } catch (e) {
      setError(apiErrorMessage(e, "Registration failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Center h="100vh" p="md">
      <Paper withBorder shadow="md" p="xl" radius="lg" w={420} maw="100%">
        <Stack align="center" mb="lg">
          <IconSparkles size={36} color="var(--mantine-color-violet-6)" />
          <Title order={2}>Create your account</Title>
          <Text c="dimmed" size="sm">
            Start writing smarter content
          </Text>
        </Stack>
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Full name"
              placeholder="Ada Lovelace"
              {...form.getInputProps("full_name")}
            />
            <TextInput
              label="Email"
              placeholder="you@example.com"
              {...form.getInputProps("email")}
            />
            <PasswordInput
              label="Password"
              placeholder="At least 8 characters"
              {...form.getInputProps("password")}
            />
            {error && (
              <Text c="red" size="sm">
                {error}
              </Text>
            )}
            <Button type="submit" fullWidth loading={loading}>
              Create account
            </Button>
            <Text size="sm" ta="center" c="dimmed">
              Already have an account?{" "}
              <Anchor component={Link} to="/login">
                Sign in
              </Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}
