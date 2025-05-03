import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import RequireAuth from "./components/auth/RequireAuth";
import AdminRoute from "./components/auth/AdminRoute";
import MainLayout from "./components/layout/MainLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Rooms from "./pages/Rooms";
import RoomDetail from "./pages/RoomDetails";
import ReservationsList from "./pages/ReservationsList";
import ReservationDetails from "./pages/ReservationDetails";
import NewReservation from "./pages/NewReservation";
import EditReservation from "./pages/EditReservation";
import Users from "./pages/Users";

function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* Protected routes */}
        <Route element={<RequireAuth />}>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />

            <Route path="/rooms" element={<Rooms />} />
            <Route path="/rooms/:id" element={<RoomDetail />} />

            <Route path="/reservations/new" element={<NewReservation />} />
            <Route
              path="/reservations/edit/:id"
              element={<EditReservation />}
            />
            <Route path="/reservations/:id" element={<ReservationDetails />} />
            <Route path="/reservations" element={<ReservationsList />} />

            {/* Admin-only routes */}
            <Route element={<AdminRoute />}>
              <Route path="/users" element={<Users />} />
            </Route>
          </Route>
        </Route>

        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <Toaster />
    </>
  );
}

export default App;
