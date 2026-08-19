import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { ApiKeyGate } from "./components/ApiKeyGate";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Discovery } from "./pages/Discovery";
import { Events } from "./pages/Events";
import { Live } from "./pages/Live";
import { PersonDetail } from "./pages/PersonDetail";
import { Persons } from "./pages/Persons";
import { Settings } from "./pages/Settings";
import { Zones } from "./pages/Zones";
import { applyTheme, getTheme } from "./lib/theme";
import "./styles/global.css";

applyTheme(getTheme());

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "live", element: <Live /> },
      { path: "zones", element: <Zones /> },
      { path: "discovery", element: <Discovery /> },
      { path: "persons", element: <Persons /> },
      { path: "persons/:id", element: <PersonDetail /> },
      { path: "events", element: <Events /> },
      { path: "settings", element: <Settings /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ApiKeyGate>
        <RouterProvider router={router} />
      </ApiKeyGate>
    </QueryClientProvider>
  </React.StrictMode>,
);
