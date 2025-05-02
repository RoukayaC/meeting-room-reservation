import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X, Users } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getRooms, checkRoomAvailability } from "../../services/roomService";
import { createReservation, updateReservation } from "../../services/reservationService";

function ReservationForm({ reservation = null, isEditing = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const searchParams = new URLSearchParams(location.search);
  const preselectedRoomId = searchParams.get("room");
  
  // Form state
  const [formData, setFormData] = useState({
    room_id: preselectedRoomId || (reservation ? reservation.room_id : ""),
    title: reservation ? reservation.title : "",
    description: reservation ? reservation.description || "" : "",
    start_date: "",
    start_time: "",
    end_date: "",
    end_time: "",
    attendees: reservation?.attendees || []
  });
  
  // Initial dates formatting for form
  useEffect(() => {
    if (reservation) {
      const startDate = new Date(reservation.start_time);
      const endDate = new Date(reservation.end_time);
      
      setFormData(prev => ({
        ...prev,
        start_date: startDate.toISOString().split("T")[0],
        start_time: startDate.toTimeString().slice(0, 5),
        end_date: endDate.toISOString().split("T")[0],
        end_time: endDate.toTimeString().slice(0, 5)
      }));
    }
  }, [reservation]);
  
  // Form errors state
  const [errors, setErrors] = useState({});
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  const [isAvailable, setIsAvailable] = useState(true);
  
  // New attendee form
  const [newAttendee, setNewAttendee] = useState({
    email: "",
    name: ""
  });
  
  // Fetch rooms
  const { data: rooms, isLoading: isLoadingRooms } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => getRooms()
  });
  
  // Create reservation mutation
  const createMutation = useMutation({
    mutationFn: createReservation,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      navigate(`/reservations/${data.id}`);
    }
  });
  
  // Update reservation mutation
  const updateMutation = useMutation({
    mutationFn: (data) => updateReservation(reservation.id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      queryClient.invalidateQueries({ queryKey: ["reservation", reservation.id] });
      navigate(`/reservations/${data.id}`);
    }
  });
  
  // Handle input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    
    // Clear errors for this field
    if (errors[name]) {
      setErrors({ ...errors, [name]: null });
    }
    
    // Reset availability check when room or date/time changes
    if (["room_id", "start_date", "start_time", "end_date", "end_time"].includes(name)) {
      setIsAvailable(true);
    }
  };
  
  // Handle new attendee fields change
  const handleAttendeeChange = (e) => {
    const { name, value } = e.target;
    setNewAttendee({ ...newAttendee, [name]: value });
  };
  
  // Add attendee to the list
  const addAttendee = () => {
    if (!newAttendee.email) {
      return;
    }
    
    // Check if email already exists
    const emailExists = formData.attendees.some(
      attendee => attendee.email === newAttendee.email
    );
    
    if (emailExists) {
      setErrors({ ...errors, attendeeEmail: "This email is already added" });
      return;
    }
    
    // Add new attendee
    setFormData({
      ...formData,
      attendees: [
        ...formData.attendees,
        {
          id: `temp-${Date.now()}`, // Temporary ID for UI
          email: newAttendee.email,
          name: newAttendee.name,
          user_id: null
        }
      ]
    });
    
    // Reset new attendee form
    setNewAttendee({ email: "", name: "" });
    setErrors({ ...errors, attendeeEmail: null });
  };
  
  // Remove attendee from the list
  const removeAttendee = (attendeeEmail) => {
    setFormData({
      ...formData,
      attendees: formData.attendees.filter(
        attendee => attendee.email !== attendeeEmail
      )
    });
  };
  
  // Check room availability
  const checkAvailability = async () => {
    const { room_id, start_date, start_time, end_date, end_time } = formData;
    
    if (!room_id || !start_date || !start_time || !end_date || !end_time) {
      setErrors({
        ...errors,
        availability: "Please select a room and set the date/time to check availability"
      });
      return;
    }
    
    setIsCheckingAvailability(true);
    setErrors({ ...errors, availability: null });
    
    try {
      const startDateTime = `${start_date}T${start_time}:00`;
      const endDateTime = `${end_date}T${end_time}:00`;
      
      // Skip check if editing and time hasn't changed
      if (isEditing && 
          reservation.start_time === startDateTime && 
          reservation.end_time === endDateTime) {
        setIsAvailable(true);
        setIsCheckingAvailability(false);
        return;
      }
      
      const result = await checkRoomAvailability({
        room_id,
        start_time: startDateTime,
        end_time: endDateTime
      });
      
      setIsAvailable(result.available);
      
      if (!result.available) {
        setErrors({
          ...errors,
          availability: "This room is not available at the selected time"
        });
      }
    } catch (error) {
      setIsAvailable(false);
      setErrors({
        ...errors,
        availability: "Failed to check availability: " + (error.error?.message || "Unknown error")
      });
    } finally {
      setIsCheckingAvailability(false);
    }
  };
  
  // Validate form
  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.room_id) {
      newErrors.room_id = "Please select a room";
    }
    
    if (!formData.title) {
      newErrors.title = "Please enter a title";
    }
    
    if (!formData.start_date || !formData.start_time) {
      newErrors.start_time = "Please set a start date and time";
    }
    
    if (!formData.end_date || !formData.end_time) {
      newErrors.end_time = "Please set an end date and time";
    }
    
    // Check if end time is after start time
    const startDateTime = new Date(`${formData.start_date}T${formData.start_time}`);
    const endDateTime = new Date(`${formData.end_date}T${formData.end_time}`);
    
    if (startDateTime >= endDateTime) {
      newErrors.end_time = "End time must be after start time";
    }
    
    // Check if start time is in the future
    if (startDateTime <= new Date()) {
      newErrors.start_time = "Start time must be in the future";
    }
    
    if (!isAvailable) {
      newErrors.availability = "This room is not available at the selected time";
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    // Format data for API
    const { start_date, start_time, end_date, end_time, ...restData } = formData;
    
    const reservationData = {
      ...restData,
      start_time: `${start_date}T${start_time}:00`,
      end_time: `${end_date}T${end_time}:00`,
      attendees_count: formData.attendees.length || 1
    };
    
    // Submit form
    if (isEditing) {
      updateMutation.mutate(reservationData);
    } else {
      createMutation.mutate(reservationData);
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Room Selection */}
      <div className="space-y-2">
        <label htmlFor="room_id" className="block text-sm font-medium text-gray-700">
          Room *
        </label>
        <select
          id="room_id"
          name="room_id"
          value={formData.room_id}
          onChange={handleChange}
          className={`mt-1 block w-full px-3 py-2 border ${
            errors.room_id ? "border-red-300" : "border-gray-300"
          } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
          disabled={isEditing || isLoadingRooms}
        >
          <option value="">Select a room</option>
          {rooms?.map((room) => (
            <option key={room.id} value={room.id}>
              {room.name} ({room.capacity} people, {room.building})
            </option>
          ))}
        </select>
        {errors.room_id && (
          <p className="mt-1 text-sm text-red-600">{errors.room_id}</p>
        )}
      </div>
      
      {/* Title & Description */}
      <div className="space-y-2">
        <label htmlFor="title" className="block text-sm font-medium text-gray-700">
          Title *
        </label>
        <input
          type="text"
          id="title"
          name="title"
          value={formData.title}
          onChange={handleChange}
          className={`mt-1 block w-full px-3 py-2 border ${
            errors.title ? "border-red-300" : "border-gray-300"
          } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
          placeholder="e.g. Team Meeting, Project Review"
        />
        {errors.title && (
          <p className="mt-1 text-sm text-red-600">{errors.title}</p>
        )}
      </div>
      
      <div className="space-y-2">
        <label htmlFor="description" className="block text-sm font-medium text-gray-700">
          Description
        </label>
        <textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          rows={3}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
          placeholder="Meeting agenda, details, etc."
        />
      </div>
      
      {/* Date & Time Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
            Start Date & Time *
          </label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="date"
              id="start_date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              className={`mt-1 block w-full px-3 py-2 border ${
                errors.start_time ? "border-red-300" : "border-gray-300"
              } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
            />
            <input
              type="time"
              id="start_time"
              name="start_time"
              value={formData.start_time}
              onChange={handleChange}
              className={`mt-1 block w-full px-3 py-2 border ${
                errors.start_time ? "border-red-300" : "border-gray-300"
              } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
            />
          </div>
          {errors.start_time && (
            <p className="mt-1 text-sm text-red-600">{errors.start_time}</p>
          )}
        </div>
        
        <div className="space-y-2">
          <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">
            End Date & Time *
          </label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="date"
              id="end_date"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              className={`mt-1 block w-full px-3 py-2 border ${
                errors.end_time ? "border-red-300" : "border-gray-300"
              } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
            />
            <input
              type="time"
              id="end_time"
              name="end_time"
              value={formData.end_time}
              onChange={handleChange}
              className={`mt-1 block w-full px-3 py-2 border ${
                errors.end_time ? "border-red-300" : "border-gray-300"
              } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
            />
          </div>
          {errors.end_time && (
            <p className="mt-1 text-sm text-red-600">{errors.end_time}</p>
          )}
        </div>
      </div>
      
      {/* Availability Check */}
      <div>
        <button
          type="button"
          onClick={checkAvailability}
          disabled={isCheckingAvailability}
          className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          {isCheckingAvailability ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Checking Availability...
            </>
          ) : (
            "Check Availability"
          )}
        </button>
        
        {isAvailable && !errors.availability && (
          <span className="ml-3 text-sm text-green-600">
            {formData.room_id && formData.start_date && formData.end_date
              ? "Room is available!"
              : "Please select room and time to check availability"}
          </span>
        )}
        
        {errors.availability && (
          <p className="mt-1 text-sm text-red-600">{errors.availability}</p>
        )}
      </div>
      
      {/* Attendees */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Attendees</h3>
          <span className="text-sm text-gray-500 flex items-center">
            <Users className="h-4 w-4 mr-1" />
            {formData.attendees.length || 0} attendees
          </span>
        </div>
        
        {/* Current attendees list */}
        {formData.attendees.length > 0 && (
          <div className="bg-gray-50 p-4 rounded-md">
            <ul className="divide-y divide-gray-200">
              {formData.attendees.map((attendee) => (
                <li key={attendee.id || attendee.email} className="py-2 flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium">{attendee.name || "No name"}</p>
                    <p className="text-xs text-gray-500">{attendee.email}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAttendee(attendee.email)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Add new attendee form */}
        <div className="bg-white border border-gray-200 p-4 rounded-md">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="attendee-email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                type="email"
                id="attendee-email"
                name="email"
                value={newAttendee.email}
                onChange={handleAttendeeChange}
                className={`mt-1 block w-full px-3 py-2 border ${
                  errors.attendeeEmail ? "border-red-300" : "border-gray-300"
                } rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm`}
              />
              {errors.attendeeEmail && (
                <p className="mt-1 text-sm text-red-600">{errors.attendeeEmail}</p>
              )}
            </div>
            
            <div>
              <label htmlFor="attendee-name" className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                type="text"
                id="attendee-name"
                name="name"
                value={newAttendee.name}
                onChange={handleAttendeeChange}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
              />
            </div>
          </div>
          
          <div className="mt-4">
            <button
              type="button"
              onClick={addAttendee}
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-primary bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Attendee
            </button>
          </div>
        </div>
      </div>
      
      {/* Form Actions */}
      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Cancel
        </button>
        
        <button
          type="submit"
          disabled={createMutation.isPending || updateMutation.isPending}
          className="px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-foreground focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          {createMutation.isPending || updateMutation.isPending ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {isEditing ? "Updating..." : "Creating..."}
            </>
          ) : (
            isEditing ? "Update Reservation" : "Create Reservation"
          )}
        </button>
      </div>
    </form>
  );
}

export default ReservationForm;