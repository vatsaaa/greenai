import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ReconWorkstation from './components/ReconWorkstation';

// Create a client
const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ReconWorkstation />
    </QueryClientProvider>
  );
}

export default App;
