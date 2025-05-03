import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { getReservations } from "../../services/reservationService";
import { getRooms } from "../../services/roomService";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import Loading from "../ui/loading";
import { Reservation, Room } from "../../types/models";
import { formatDate, formatTime } from "../../lib/utils";

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [upcomingReservations, setUpcomingReservations] = useState<
    Reservation[]
  >([]);
  const [availableRooms, setAvailableRooms] = useState<Room[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);

        // Get upcoming reservations
        const today = new Date().toISOString().split("T")[0];
        const reservations = await getReservations({
          start_date: today,
        });

        // Only show user's reservations if not admin
        const filteredReservations =
          user?.role === "admin"
            ? reservations
            : reservations.filter((res) => res.user_id === user?.id);

        // Get the 5 most recent upcoming reservations
        const upcoming = filteredReservations
          .sort(
            (a, b) =>
              new Date(a.start_time).getTime() -
              new Date(b.start_time).getTime()
          )
          .slice(0, 5);

        setUpcomingReservations(upcoming);

        // Get available rooms
        const rooms = await getRooms();
        setAvailableRooms(rooms.slice(0, 5)); // Show 5 rooms
      } catch (err) {
        setError("Failed to load dashboard data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [user]);

  if (loading) {
    return <Loading size="large" className="mt-8" />;
  }

  if (error) {
    return <div className="p-4 bg-red-100 text-red-700 rounded">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold">Dashboard</h2>
        <Button asChild>
          <Link to="/reservations/new">New Reservation</Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Upcoming Reservations */}
        <Card>
          <CardHeader>
            <CardTitle>Upcoming Reservations</CardTitle>
          </CardHeader>
          <CardContent>
            {upcomingReservations.length > 0 ? (
              <div className="space-y-4">
                {upcomingReservations.map((reservation) => (
                  <Link
                    key={reservation.id}
                    to={`/reservations/${reservation.id}`}
                    className="block p-3 rounded border hover:bg-gray-50 transition-colors"
                  >
                    <p className="font-medium">{reservation.title}</p>
                    <p className="text-sm text-gray-500">
                      {formatDate(reservation.start_time)} at{" "}
                      {formatTime(reservation.start_time)}
                    </p>
                    <p className="text-sm text-gray-500">
                      Room: {reservation.room_name || `#${reservation.room_id}`}
                    </p>
                  </Link>
                ))}
                <div className="text-center mt-4">
                  <Button variant="outline" asChild>
                    <Link to="/reservations">View All</Link>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center p-4">
                <p className="text-gray-500">No upcoming reservations</p>
                <Button className="mt-2" asChild>
                  <Link to="/reservations/new">Create Reservation</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Available Rooms */}
        <Card>
          <CardHeader>
            <CardTitle>Available Rooms</CardTitle>
          </CardHeader>
          <CardContent>
            {availableRooms.length > 0 ? (
              <div className="space-y-4">
                {availableRooms.map((room) => (
                  <Link
                    key={room.id}
                    to={`/rooms/${room.id}`}
                    className="block p-3 rounded border hover:bg-gray-50 transition-colors"
                  >
                    <p className="font-medium">{room.name}</p>
                    <p className="text-sm text-gray-500">
                      {room.room_type} - Capacity: {room.capacity}
                    </p>
                    <div className="flex gap-2 mt-1">
                      {room.has_projector && (
                        <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                          Projector
                        </span>
                      )}
                      {room.has_video_conf && (
                        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded">
                          Video Conference
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
                <div className="text-center mt-4">
                  <Button variant="outline" asChild>
                    <Link to="/rooms">View All</Link>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center p-4">
                <p className="text-gray-500">No available rooms</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {user?.role === "admin" && (
        <Card>
          <CardHeader>
            <CardTitle>Admin Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button variant="secondary" asChild>
              <Link to="/users">Manage Users</Link>
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/rooms/new">Add New Room</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
