import { createBrowserRouter, Navigate } from 'react-router-dom'

import { BetsPage } from '@/features/bets/BetsPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { ModalityPage } from '@/features/dashboard/ModalityPage'
import { Layout } from './Layout'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      // Uma unica rota de modalidade, dirigida por config/modalities.ts.
      { path: 'm/:modality', element: <ModalityPage /> },
      { path: 'bets', element: <BetsPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])
