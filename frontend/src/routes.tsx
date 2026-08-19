import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { AppLayout } from './layouts/AppLayout';
import { ChatPage } from './pages/ChatPage';
import { PlanReviewPage } from './pages/PlanReviewPage';
import { ExecutionPage } from './pages/ExecutionPage';
import { PermissionsPage } from './pages/PermissionsPage';
import { ArtifactsPage } from './pages/ArtifactsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    element: <AppLayout />,
    children: [
      {
        path: '/chat',
        element: <ChatPage />,
      },
      {
        path: '/plan',
        element: <PlanReviewPage />,
      },
      {
        path: '/execution',
        element: <ExecutionPage />,
      },
      {
        path: '/runtime',
        element: <ExecutionPage />,
      },
      {
        path: '/permissions',
        element: <PermissionsPage />,
      },
      {
        path: '/artifacts',
        element: <ArtifactsPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
