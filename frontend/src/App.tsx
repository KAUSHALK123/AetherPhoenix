import { RouterProvider, createBrowserRouter } from 'react-router-dom';

const router = createBrowserRouter([
  {
    path: "/",
    element: <div className="p-4 text-center text-xl font-bold">AetherPhoenix Frontend Foundation</div>,
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
