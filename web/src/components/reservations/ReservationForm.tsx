import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { format, parseISO, addHours } from "date-fns";
import { Calendar as CalendarIcon, Clock, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getRooms, checkRoomAvailability } from "../services/roomService";
import { useAuth } from "../context/AuthContext";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Schema for form validation
const reservationFormSchema = z.object({
  roomId: z.string({
    required_error: "Please select a room",
  }),
  date: z.date({
    required_error: "Please select a date",
  }),
  startTime: z.string({
    required_error: "Please select a start time",
  }),
  endTime: z.string({
    required_error: "Please select an end time",
  }),
  purpose: z.string().min(3, "Purpose must be at least 3 characters").max(200),
  attendees: z.string().optional(),
});

export default function ReservationForm({ reservation = null, onSubmit }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [availabilityChecked, setAvailabilityChecked] = useState(false);
  const [isAvailable, setIsAvailable] = useState(true);
  const [selectedDate, setSelectedDate] = useState(
    reservation ? parseISO(reservation.start_time) : new Date()
  );

  // Time slots for selection (30 minute intervals)
  const timeSlots = [];
  for (let hour = 8; hour < 20; hour++) {
    for (let minute of [0, 30]) {
      const formattedTime = `${String(hour).padStart(2, "0")}:${String(
        minute
      ).padStart(2, "0")}`;
      timeSlots.push(formattedTime);
    }
  }

  // Form setup with default values
  const form = useForm({
    resolver: zodResolver(reservationFormSchema),
    defaultValues: {
      roomId: reservation?.room_id?.toString() || "",
      date: reservation ? parseISO(reservation.start_time) : new Date(),
      startTime: reservation
        ? format(parseISO(reservation.start_time), "HH:mm")
        : "09:00",
      endTime: reservation
        ? format(parseISO(reservation.end_time), "HH:mm")
        : "10:00",
      purpose: reservation?.purpose || "",
      attendees: reservation?.attendees
        ? reservation.attendees.map((a) => a.email).join(", ")
        : "",
    },
  });

  // Fetch rooms
  const { data: rooms = [], isLoading: roomsLoading } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => getRooms({ capacity: 1 }), // Get all rooms with at least capacity 1
  });

  // Watch form values to check availability when they change
  const roomId = form.watch("roomId");
  const date = form.watch("date");
  const startTime = form.watch("startTime");
  const endTime = form.watch("endTime");

  // Check room availability when key fields change
  useEffect(() => {
    if (!roomId || !date || !startTime || !endTime) {
      setAvailabilityChecked(false);
      return;
    }

    const checkAvailability = async () => {
      try {
        // Format date + time combinations for API
        const startDateTime = new Date(date);
        const [startHours, startMinutes] = startTime.split(":").map(Number);
        startDateTime.setHours(startHours, startMinutes);

        const endDateTime = new Date(date);
        const [endHours, endMinutes] = endTime.split(":").map(Number);
        endDateTime.setHours(endHours, endMinutes);

        // Skip check if we're editing the same reservation
        if (
          reservation &&
          reservation.id &&
          reservation.room_id.toString() === roomId
        ) {
          const reservationStart = parseISO(reservation.start_time);
          const reservationEnd = parseISO(reservation.end_time);

          if (
            startDateTime.getTime() === reservationStart.getTime() &&
            endDateTime.getTime() === reservationEnd.getTime()
          ) {
            setIsAvailable(true);
            setAvailabilityChecked(true);
            return;
          }
        }

        const result = await checkRoomAvailability({
          room_id: roomId,
          start_time: startDateTime.toISOString(),
          end_time: endDateTime.toISOString(),
          exclude_reservation_id: reservation?.id,
        });

        setIsAvailable(result.available);
        setAvailabilityChecked(true);
      } catch (error) {
        console.error("Failed to check availability:", error);
        setIsAvailable(false);
        setAvailabilityChecked(true);
      }
    };

    checkAvailability();
  }, [roomId, date, startTime, endTime, reservation]);

  // Handle form submission
  const handleSubmit = (data) => {
    if (!isAvailable && availabilityChecked) {
      toast.error("This room is not available for the selected time");
      return;
    }

    try {
      // Format date + time combinations for API
      const startDateTime = new Date(data.date);
      const [startHours, startMinutes] = data.startTime.split(":").map(Number);
      startDateTime.setHours(startHours, startMinutes);

      const endDateTime = new Date(data.date);
      const [endHours, endMinutes] = data.endTime.split(":").map(Number);
      endDateTime.setHours(endHours, endMinutes);

      // Parse attendees from comma-separated string
      const attendees = data.attendees
        ? data.attendees.split(",").map((email) => ({ email: email.trim() }))
        : [];

      const reservationData = {
        room_id: parseInt(data.roomId),
        start_time: startDateTime.toISOString(),
        end_time: endDateTime.toISOString(),
        purpose: data.purpose,
        attendees,
      };

      // Call the onSubmit handler passed from parent
      onSubmit(reservationData);
    } catch (error) {
      toast.error("Error processing form data");
      console.error("Form submission error:", error);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        {/* Room Selection */}
        <FormField
          control={form.control}
          name="roomId"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Meeting Room</FormLabel>
              <Select
                onValueChange={field.onChange}
                defaultValue={field.value}
                disabled={roomsLoading}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a room" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {roomsLoading ? (
                    <SelectItem value="loading" disabled>
                      Loading...
                    </SelectItem>
                  ) : (
                    rooms.map((room) => (
                      <SelectItem key={room.id} value={room.id.toString()}>
                        {room.name} ({room.capacity} people)
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Date Selection */}
        <FormField
          control={form.control}
          name="date"
          render={({ field }) => (
            <FormItem className="flex flex-col">
              <FormLabel>Date</FormLabel>
              <Popover>
                <PopoverTrigger asChild>
                  <FormControl>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full pl-3 text-left font-normal",
                        !field.value && "text-muted-foreground"
                      )}
                    >
                      {field.value ? (
                        format(field.value, "PPP")
                      ) : (
                        <span>Pick a date</span>
                      )}
                      <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={field.value}
                    onSelect={(date) => {
                      field.onChange(date);
                      setSelectedDate(date);
                    }}
                    disabled={(date) =>
                      date < new Date(new Date().setHours(0, 0, 0, 0))
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Time Range Selection */}
        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="startTime"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Start Time</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Start time" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {timeSlots.map((time) => (
                      <SelectItem key={`start-${time}`} value={time}>
                        {time}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="endTime"
            render={({ field }) => (
              <FormItem>
                <FormLabel>End Time</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="End time" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {timeSlots
                      .filter((time) => time > form.getValues("startTime"))
                      .map((time) => (
                        <SelectItem key={`end-${time}`} value={time}>
                          {time}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Show availability status */}
        {roomId && availabilityChecked && (
          <div className="my-2">
            {isAvailable ? (
              <Badge className="bg-green-500">Room available</Badge>
            ) : (
              <Badge className="bg-red-500">Room not available</Badge>
            )}
          </div>
        )}

        {/* Purpose field */}
        <FormField
          control={form.control}
          name="purpose"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Purpose</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Purpose of the meeting"
                  className="resize-none"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Attendees field */}
        <FormField
          control={form.control}
          name="attendees"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Attendees (optional)</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Email addresses, comma separated"
                  className="resize-none"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button type="submit">
            {form.formState.isSubmitting && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {reservation ? "Update Reservation" : "Create Reservation"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
