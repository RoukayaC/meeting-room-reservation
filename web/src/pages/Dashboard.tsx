import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Calendar, Users, Grid3X3 } from "lucide-react";
import { formatDate } from "../lib/utils";
import { getReservations } from "../services/reservationService";
import { getRooms } from "../services/roomService";
import { useAuth } from "../context/AuthContext";

function Dashboard() {
  const { user } = useAuth();
  const [upcomingReservations, setUpcomingReservations] = useState([]);

  // Fetch user's upcoming reservations
  const { data: reservations, isLoading: isLoadingReservations } = useQuery({
    queryKey: ["user-reservations"],
    queryFn: () => getReservations({ status: "confirmed" }),
  });

  // Fetch all rooms
  const { data: rooms, isLoading: isLoadingRooms } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => getRooms(),
  });

  // Set upcoming reservations
  useEffect(() => {
    if (reservations) {
      // Sort by start time and take only the next 5
      const upcoming = [...reservations]
        .filter(res => new Date(res.start_time) > new Date())
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
        .slice(0, 5);
      
      setUpcomingReservations(upcoming);
    }
  }, [reservations]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 justify-between md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.first_name || "User"}!
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/reservations/new"
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-foreground"
          >
            New Reservation
          </Link>
        </div>
      </div>

      {/* Dashboard Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center space-x-2">
            <Calendar className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-medium">Upcoming Reservations</h3>
          </div>
          <p className="text-3xl font-bold mt-2">
            {isLoadingReservations ? "..." : upcomingReservations.length}
          </p>
          <p className="text-muted-foreground text-sm">
            {isLoadingReservations ? "Loading..." : "Next 5 reservations"}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center space-x-2">
            <Grid3X3 className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-medium">Available Rooms</h3>
          </div>
          <p className="text-3xl font-bold mt-2">
            {isLoadingRooms ? "..." : rooms?.length || 0}
          </p>
          <p className="text-muted-foreground text-sm">
            {isLoadingRooms ? "Loading..." : "Total rooms"}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center space-x-2">
            <Users className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-medium">My Reservations</h3>
          </div>
          <p className="text-3xl font-bold mt-2">
            {isLoadingReservations ? "..." : reservations?.length || 0}
          </p>
          <p className="text-muted-foreground text-sm">
            {isLoadingReservations ? "Loading..." : "Total reservations"}
          </p>
        </div>
      </div>

      {/* Upcoming Reservations */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium">Your Upcoming Reservations</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {isLoadingReservations ? (
            <div className="p-6 text-center">Loading...</div>
          ) : upcomingReservations.length > 0 ? (
            upcomingReservations.map((reservation) => (
              <div key={reservation.id} className="p-6 flex justify-between items-center">
                <div>
                  <h4 className="font-medium">{reservation.title}</h4>
                  <p className="text-sm text-gray-500">
                    {formatDate(reservation.start_time)} - Room #{reservation.room_id}
                  </p>
                </div>
                <Link
                  to={`/reservations/${reservation.id}`}
                  className="px-3 py-1 text-sm rounded bg-primary text-white"
                >
                  View
                </Link>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-muted-foreground">
              No upcoming reservations found
            </div>
          )}
        </div>
        <div className="p-4 bg-gray-50 border-t border-gray-200">
          <Link
            to="/reservations"
            className="text-primary hover:text-primary-foreground text-sm font-medium"
          >
            View all reservations →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;