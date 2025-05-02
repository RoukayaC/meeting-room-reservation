import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Calendar, Edit, Trash2, Users, Clock } from "lucide-react";
import { getReservationById, cancelReservation } from "../services/reservationService";
import { getRoomById } from "../services/roomService";
import { formatDate, formatTime } from "../lib/utils";
import { useAuth } from "../context/AuthContext";

function ReservationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isAdmin } = useAuth();
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  
  // Fetch reservation details
  const { data: reservation, isLoading: isLoadingReservation } = useQuery({
    queryKey: ["reservation", id],
    queryFn: () => getReservationById(id),
  });
  
  // Fetch room details if reservation is loaded
  const { data: room, isLoading: isLoadingRoom } = useQuery({
    queryKey: ["room", reservation?.room_id],
    queryFn: () => getRoomById(reservation.room_id),
    enabled: !!reservation?.room_id,
  });
  
  // Cancel reservation mutation
  const cancelMutation = useMutation({
    mutationFn: cancelReservation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      queryClient.invalidateQueries({ queryKey: ["reservation", id] });
    },
  });
  
  // Check if user can edit/cancel the reservation
  const canManageReservation = () => {
    if (!reservation || !user) return false;
    return isAdmin() || reservation.user_id === user.id;
  };
  
  // Check if reservation can be cancelled (not in the past and not already cancelled)
  const canCancel = () => {
    if (!reservation) return false;
    return (
      canManageReservation() &&
      reservation.status !== "cancelled" &&
      reservation.status !== "completed" &&
      new Date(reservation.start_time) > new Date()
    );
  };
  
  if (isLoadingReservation || (reservation && isLoadingRoom)) {
    return (
      <div className="grid place-items-center h-64">
        <div className="w-16 h-16 border-4 border-primary border-solid rounded-full border-t-transparent animate-spin"></div>
      </div>
    );
  }
  
  if (!reservation) {
    return (
      <div className="bg-white p-10 text-center rounded-lg shadow">
        <h3 className="text-lg font-medium mb-2">Reservation not found</h3>
        <p className="text-muted-foreground mb-4">This reservation may have been deleted.</p>
        <Link to="/reservations" className="text-primary hover:text-primary-foreground">
          Back to Reservations
        </Link>
      </div>
    );
  }
  
  // Get status badge classes
  const getStatusBadgeClass = () => {
    switch (reservation.status) {
      case "confirmed":
        return "bg-green-100 text-green-800";
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "cancelled":
        return "bg-red-100 text-red-800";
      case "completed":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 justify-between md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{reservation.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full capitalize ${getStatusBadgeClass()}`}>
              {reservation.status}
            </span>
            <span className="text-sm text-muted-foreground">
              Reservation #{reservation.id}
            </span>
          </div>
        </div>
        
        <div className="flex gap-2">
          {canManageReservation() && reservation.status === "confirmed" && (
            <Link
              to={`/reservations/${reservation.id}/edit`}
              className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            >
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Link>
          )}
          
          {canCancel() && (
            <button
              onClick={() => setShowCancelConfirm(true)}
              className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-red-600 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Cancel Reservation
            </button>
          )}
        </div>
      </div>
      
      {/* Reservation Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          {/* Main Reservation Info */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium mb-4">Reservation Information</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Title</p>
                <p className="font-medium">{reservation.title}</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Status</p>
                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full capitalize ${getStatusBadgeClass()}`}>
                  {reservation.status}
                </span>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Date & Time</p>
                <div className="flex items-start gap-1">
                  <Calendar className="h-4 w-4 mt-0.5 text-gray-400" />
                  <div>
                    <p>{formatDate(reservation.start_time)}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      <Clock className="h-3 w-3 inline mr-1" />
                      {formatTime(reservation.start_time)} - {formatTime(reservation.end_time)}
                    </p>
                  </div>
                </div>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Room</p>
                <p className="font-medium">
                  {room ? room.name : `Room #${reservation.room_id}`}
                </p>
                {room && (
                  <p className="text-sm text-gray-500 mt-1">
                    {room.building}, {room.floor} Floor
                  </p>
                )}
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Created By</p>
                <p>User #{reservation.user_id}</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Attendees</p>
                <div className="flex items-center">
                  <Users className="h-4 w-4 mr-2 text-gray-400" />
                  {reservation.attendees_count || 1} people
                </div>
              </div>
            </div>
            
            {reservation.description && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-sm text-gray-500">Description</p>
                <p className="mt-1 whitespace-pre-line">{reservation.description}</p>
              </div>
            )}
          </div>
          
          {/* Attendees List */}
          {reservation.attendees && reservation.attendees.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-medium">Attendees</h2>
              </div>
              
              <ul className="divide-y divide-gray-200">
                {reservation.attendees.map((attendee) => (
                  <li key={attendee.id} className="p-4">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                        <Users className="h-5 w-5 text-gray-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {attendee.name || "Unnamed Attendee"}
                        </p>
                        <p className="text-sm text-gray-500 truncate">
                          {attendee.email}
                        </p>
                      </div>
                      {attendee.user_id && (
                        <div className="inline-flex items-center text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                          User #{attendee.user_id}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        
        {/* Room Information Sidebar */}
        {room && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-medium">Room Information</h2>
            </div>
            
            <div className="p-6">
              <h3 className="font-medium text-lg mb-2">{room.name}</h3>
              <p className="text-sm text-gray-500 mb-4">
                {room.building}, {room.floor} Floor
              </p>
              
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500">Room Type</p>
                  <p className="capitalize">{room.room_type}</p>
                </div>
                
                <div>
                  <p className="text-sm text-gray-500">Capacity</p>
                  <p className="flex items-center">
                    <Users className="h-4 w-4 mr-2 text-gray-400" />
                    {room.capacity} people
                  </p>
                </div>
                
                <div>
                  <p className="text-sm text-gray-500">Features</p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {room.has_projector && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Projector
                      </span>
                    )}
                    
                    {room.has_video_conf && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Video Conference
                      </span>
                    )}
                    
                    {room.has_whiteboard && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        Whiteboard
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-gray-50 border-t border-gray-200">
              <Link
                to={`/rooms/${room.id}`}
                className="text-primary hover:text-primary-foreground text-sm font-medium"
              >
                View room details →
              </Link>
            </div>
          </div>
        )}
      </div>
      
      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h3 className="text-lg font-medium mb-4">Cancel Reservation</h3>
            <p className="mb-4">
              Are you sure you want to cancel this reservation for <strong>{room?.name || `Room #${reservation.room_id}`}</strong>? This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Keep Reservation
              </button>
              <button
                onClick={() => {
                  cancelMutation.mutate(reservation.id);
                  setShowCancelConfirm(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700"
                disabled={cancelMutation.isPending}
              >
                {cancelMutation.isPending ? "Cancelling..." : "Yes, Cancel"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReservationDetail;