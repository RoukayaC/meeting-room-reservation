import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Calendar, Edit, Trash2, Check, X, Users, Monitor, Eraser } from "lucide-react";
import { getRoomById, deleteRoom, getRoomUnavailability } from "../services/roomService";
import { getRoomReservations } from "../services/reservationService";
import { formatDate } from "../lib/utils";
import { useAuth } from "../context/AuthContext";

function RoomDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // Fetch room details
  const { data: room, isLoading } = useQuery({
    queryKey: ["room", id],
    queryFn: () => getRoomById(id),
  });
  
  // Fetch room reservations for the next 7 days
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 7);
  const { data: reservations, isLoading: isLoadingReservations } = useQuery({
    queryKey: ["room-reservations", id],
    queryFn: () => getRoomReservations(id, {
      start_date: new Date().toISOString(),
      end_date: endDate.toISOString()
    }),
  });
  
  // Fetch room unavailability periods
  const { data: unavailability, isLoading: isLoadingUnavailability } = useQuery({
    queryKey: ["room-unavailability", id],
    queryFn: () => getRoomUnavailability(id),
  });
  
  // Delete room mutation
  const deleteMutation = useMutation({
    mutationFn: deleteRoom,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
      navigate("/rooms");
    },
  });
  
  if (isLoading) {
    return (
      <div className="grid place-items-center h-64">
        <div className="w-16 h-16 border-4 border-primary border-solid rounded-full border-t-transparent animate-spin"></div>
      </div>
    );
  }
  
  if (!room) {
    return (
      <div className="bg-white p-10 text-center rounded-lg shadow">
        <h3 className="text-lg font-medium mb-2">Room not found</h3>
        <p className="text-muted-foreground mb-4">This room may have been deleted.</p>
        <Link to="/rooms" className="text-primary hover:text-primary-foreground">
          Back to Rooms
        </Link>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 justify-between md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{room.name}</h1>
          <p className="text-muted-foreground">
            {room.building}, {room.floor} Floor
          </p>
        </div>
        
        <div className="flex gap-2">
          <Link
            to={`/reservations/new?room=${room.id}`}
            className="inline-flex items-center rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-foreground"
          >
            <Calendar className="h-4 w-4 mr-2" />
            Book Room
          </Link>
          
          {isAdmin() && (
            <>
              <Link
                to={`/rooms/${room.id}/edit`}
                className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
              >
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Link>
              
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-red-600 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </button>
            </>
          )}
        </div>
      </div>
      
      {/* Room Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          {/* Room Info */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium mb-4">Room Information</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Room Type</p>
                <p className="capitalize">{room.room_type}</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Capacity</p>
                <p className="flex items-center">
                  <Users className="h-4 w-4 mr-2" />
                  {room.capacity} people
                </p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Features</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {room.has_projector && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      <Monitor className="h-3 w-3 mr-1" /> Projector
                    </span>
                  )}
                  
                  {room.has_video_conf && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      <Monitor className="h-3 w-3 mr-1" /> Video Conference
                    </span>
                  )}
                  
                  {room.has_whiteboard && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                      <Eraser className="h-3 w-3 mr-1" /> Whiteboard
                    </span>
                  )}
                </div>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Location</p>
                <p>
                  {room.building}, {room.floor} Floor
                </p>
              </div>
            </div>
            
            {room.description && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-sm text-gray-500">Description</p>
                <p className="mt-1">{room.description}</p>
              </div>
            )}
          </div>
          
          {/* Upcoming Reservations */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-medium">Upcoming Reservations</h2>
            </div>
            
            <div className="divide-y divide-gray-200">
              {isLoadingReservations ? (
                <div className="p-6 text-center">Loading...</div>
              ) : reservations?.length > 0 ? (
                reservations.map((reservation) => (
                  <div key={reservation.id} className="p-6 flex justify-between items-center">
                    <div>
                      <h4 className="font-medium">{reservation.title}</h4>
                      <p className="text-sm text-gray-500">
                        {formatDate(reservation.start_time)} - {formatDate(reservation.end_time)}
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
                  No upcoming reservations for this room
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Unavailability Periods */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-medium">Unavailability Periods</h2>
            <p className="text-sm text-gray-500">
              Times when this room is not available
            </p>
          </div>
          
          <div className="divide-y divide-gray-200">
            {isLoadingUnavailability ? (
              <div className="p-6 text-center">Loading...</div>
            ) : unavailability?.length > 0 ? (
              unavailability.map((period) => (
                <div key={period.id} className="p-4">
                  <div className="flex justify-between">
                    <p className="text-sm font-medium">{period.reason}</p>
                    {isAdmin() && (
                      <button
                        className="text-red-600 hover:text-red-900"
                        onClick={() => {/* Handle delete unavailability */}}
                      >
                        <X size={16} />
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    {formatDate(period.start_time)} - {formatDate(period.end_time)}
                  </p>
                </div>
              ))
            ) : (
              <div className="p-6 text-center text-muted-foreground">
                No unavailability periods
              </div>
            )}
          </div>
          
          {isAdmin() && (
            <div className="p-4 bg-gray-50 border-t border-gray-200">
              <button
                className="text-primary hover:text-primary-foreground text-sm font-medium"
                onClick={() => {/* Open add unavailability modal */}}
              >
                Add unavailability period +
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h3 className="text-lg font-medium mb-4">Delete Room</h3>
            <p className="mb-4">
              Are you sure you want to delete <strong>{room.name}</strong>? This action cannot be undone.
            </p>
            <p className="mb-4 text-sm text-red-600">
              Note: All associated reservations will be cancelled.
            </p>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(room.id)}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RoomDetail;