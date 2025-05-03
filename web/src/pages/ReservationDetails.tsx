import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Calendar, Clock, Users, MapPin, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import {
  getReservationById,
  updateReservation,
  cancelReservation,
} from "../services/reservationService";
import { getRoomById } from "../services/roomService";
import { useAuth } from "../context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function ReservationDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  // Fetch reservation details
  const {
    data: reservation,
    isLoading: reservationLoading,
    error: reservationError,
  } = useQuery({
    queryKey: ["reservation", id],
    queryFn: () => getReservationById(id),
  });

  // Fetch room details if reservation is loaded
  const { data: room, isLoading: roomLoading } = useQuery({
    queryKey: ["room", reservation?.room_id],
    queryFn: () => getRoomById(reservation?.room_id),
    enabled: !!reservation?.room_id,
  });

  // Mutation for canceling a reservation
  const cancelMutation = useMutation({
    mutationFn: () => cancelReservation(id),
    onSuccess: () => {
      toast.success("Reservation canceled successfully");
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      navigate("/reservations");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to cancel reservation");
    },
  });

  // Determine if current user can edit/cancel this reservation
  const canModify = () => {
    if (!reservation || !user) return false;
    return isAdmin() || reservation.user_id === user.id;
  };

  // Get status badge color
  const getStatusBadge = (status) => {
    switch (status) {
      case "CONFIRMED":
        return <Badge className="bg-green-500">Confirmed</Badge>;
      case "PENDING":
        return <Badge className="bg-yellow-500">Pending</Badge>;
      case "CANCELED":
        return <Badge className="bg-red-500">Canceled</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  if (reservationLoading || roomLoading) {
    return <div className="p-8">Loading reservation details...</div>;
  }

  if (reservationError) {
    return (
      <div className="p-8 flex flex-col items-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-2xl font-bold">Error Loading Reservation</h2>
        <p className="text-gray-600">
          There was a problem loading this reservation.
        </p>
        <Button onClick={() => navigate("/reservations")} className="mt-4">
          Back to Reservations
        </Button>
      </div>
    );
  }

  if (!reservation) {
    return (
      <div className="p-8 flex flex-col items-center">
        <AlertCircle className="h-12 w-12 text-amber-500 mb-4" />
        <h2 className="text-2xl font-bold">Reservation Not Found</h2>
        <p className="text-gray-600">
          The reservation you're looking for doesn't exist or has been removed.
        </p>
        <Button onClick={() => navigate("/reservations")} className="mt-4">
          Back to Reservations
        </Button>
      </div>
    );
  }

  const formattedStartTime = format(
    new Date(reservation.start_time),
    "MMM dd, yyyy hh:mm a"
  );
  const formattedEndTime = format(
    new Date(reservation.end_time),
    "MMM dd, yyyy hh:mm a"
  );

  return (
    <div className="container max-w-4xl mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Reservation #{id}</h1>
          <div className="flex items-center gap-2 mt-2">
            <p className="text-muted-foreground">Status:</p>
            {getStatusBadge(reservation.status)}
          </div>
        </div>

        {canModify() && reservation.status !== "CANCELED" && (
          <div className="space-x-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/reservations/edit/${id}`)}
            >
              Edit
            </Button>
            <Button
              variant="destructive"
              onClick={() => setIsDeleteDialogOpen(true)}
            >
              Cancel Reservation
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Reservation Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Time</p>
                <p>From: {formattedStartTime}</p>
                <p>To: {formattedEndTime}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Room</p>
                <p>{room?.name || "Loading..."}</p>
                {room && (
                  <p className="text-sm text-muted-foreground">
                    {room.floor}
                    {room.building ? `, ${room.building}` : ""}
                  </p>
                )}
              </div>
            </div>

            {reservation.purpose && (
              <div className="flex items-start gap-3">
                <div className="h-5 w-5 flex-shrink-0" />
                <div>
                  <p className="font-semibold">Purpose</p>
                  <p>{reservation.purpose}</p>
                </div>
              </div>
            )}

            {reservation.attendees && reservation.attendees.length > 0 && (
              <div className="flex items-start gap-3">
                <Users className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Attendees</p>
                  <ul className="list-disc list-inside">
                    {reservation.attendees.map((attendee) => (
                      <li key={attendee.id || attendee.email}>
                        {attendee.name || attendee.email}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Room Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {room ? (
              <>
                <p>
                  <span className="font-medium">Capacity:</span> {room.capacity}{" "}
                  people
                </p>
                <p>
                  <span className="font-medium">Type:</span> {room.room_type}
                </p>

                <div className="mt-4">
                  <p className="font-medium mb-2">Equipment:</p>
                  <ul className="space-y-1 text-sm">
                    {room.has_projector && <li>• Projector</li>}
                    {room.has_video_conf && <li>• Video conferencing</li>}
                    {room.has_whiteboard && <li>• Whiteboard</li>}
                  </ul>
                </div>
              </>
            ) : (
              <p>Loading room information...</p>
            )}
          </CardContent>
        </Card>
      </div>

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Reservation</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to cancel this reservation? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No, keep it</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-500 hover:bg-red-600"
              onClick={() => cancelMutation.mutate()}
            >
              Yes, cancel reservation
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
