'use client';

/**
 * Example usage of FloatingChat component
 *
 * Add this to any page where you want the chat assistant
 */

import FloatingChat from './FloatingChat';

export default function PageWithChat() {
  // Example: You might get these from your app state or URL params
  const currentIssueId = 'INC0012345'; // or null if no issue selected
  const currentIssueTitle = 'API Gateway 502 errors';

  return (
    <div>
      {/* Your page content here */}
      <h1>My Page</h1>

      {/* Floating Chat - Always visible at bottom-right */}
      <FloatingChat
        issueId={currentIssueId}
        issueTitle={currentIssueTitle}
        apiBase="http://10.128.0.57:8000"  // Your server IP
      />
    </div>
  );
}

/**
 * To add to an existing page:
 *
 * 1. Import the component:
 *    import FloatingChat from '@/components/chat/FloatingChat';
 *
 * 2. Add it anywhere in your JSX (preferably at the bottom):
 *    <FloatingChat
 *      issueId={selectedIssue?.id}
 *      issueTitle={selectedIssue?.title}
 *      apiBase="http://10.128.0.57:8000"
 *    />
 *
 * The chat will float at the bottom-right corner of the screen!
 */
