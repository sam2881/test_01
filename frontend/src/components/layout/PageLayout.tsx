import { ReactNode } from 'react'
import { Header } from './Header'

interface PageLayoutProps {
  title?: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
}

export function PageLayout({ title, subtitle, children, actions }: PageLayoutProps) {
  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Header title={title} subtitle={subtitle} />

      <main className="flex-1 bg-gray-50 p-6">
        {actions && (
          <div className="mb-6 flex items-center justify-between">
            <div />
            {actions}
          </div>
        )}

        {children}
      </main>
    </div>
  )
}
