import {
  ActionIcon,
  AppShell,
  Avatar,
  Box,
  Burger,
  Group,
  Menu,
  NavLink,
  Text,
  Title,
  useMantineColorScheme,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconArticle,
  IconLogout,
  IconMoon,
  IconSettings,
  IconSparkles,
  IconSun,
} from "@tabler/icons-react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const [opened, { toggle }] = useDisclosure();
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();

  const nav = [
    { label: "My Content", to: "/", icon: IconArticle },
    { label: "Generate", to: "/generate", icon: IconSparkles },
  ];

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <IconSparkles size={24} color="var(--mantine-color-violet-6)" />
            <Title order={4}>AI Content Writer</Title>
          </Group>
          <Group>
            <ActionIcon
              variant="subtle"
              size="lg"
              onClick={() => toggleColorScheme()}
              aria-label="Toggle color scheme"
            >
              {colorScheme === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
            <Menu shadow="md" width={200}>
              <Menu.Target>
                <Avatar color="violet" radius="xl" style={{ cursor: "pointer" }}>
                  {(user?.full_name || user?.email || "?").charAt(0).toUpperCase()}
                </Avatar>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{user?.email}</Menu.Label>
                <Menu.Item
                  leftSection={<IconSettings size={16} />}
                  onClick={() => navigate("/settings")}
                >
                  Settings
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item
                  leftSection={<IconLogout size={16} />}
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                >
                  Log out
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            component={Link}
            to={item.to}
            label={item.label}
            leftSection={<item.icon size={18} />}
            active={location.pathname === item.to}
            onClick={() => opened && toggle()}
          />
        ))}
        <Box mt="auto" pt="md">
          <Text size="xs" c="dimmed">
            v0.1.0
          </Text>
        </Box>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
