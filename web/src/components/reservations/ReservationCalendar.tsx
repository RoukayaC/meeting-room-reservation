import { useState, useEffect } from "react";
import { Calendar, dateFnsLocalizer } from "react-big-calendar";
import { format, parse, startOfWeek, getDay, parseISO } from "date-fns";
import enUS from "date-fns/locale/en-US";
import "react-big-calendar/lib/css/react-big-calendar.css";
import { getReservations } from "../../services/reservationService";
import { Reservation } from "../../types/models";
import Loading from "../ui/loading";
import { getErrorMessage } from "../../lib/utils";
import { useAuth } from "../../context/AuthContext";
import { useNavigate } from "react-router-dom";

// Setup the localizer for react-big-calendar
const locales = {
  "en-US": enUS,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

const ReservationCalendar = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchReservations = async () => {
      try {
        setLoading(true);
        const reservations = await getReservations();

        // Convert reservations to events format expected by react-big-calendar
        const calendarEvents = reservations.map((reservation: Reservation) => ({
          id: reservation.id,
          title: reservation.title,
          start: parseISO(reservation.start_time),
          end: parseISO(reservation.end_time),
          resource: reservation,
        }));

        setEvents(calendarEvents);
      } catch (err) {
        setError(getErrorMessage(err));
        console.error("Error fetching reservations:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchReservations();
  }, []);

  const handleEventSelect = (event: any) => {
    navigate(`/reservations/${event.id}`);
  };

  const eventStyleGetter = (event: any) => {
    const isUserReservation = event.resource.user_id === user?.id;

    let backgroundColor = "#3174ad"; // default color

    // If the reservation belongs to the current user, use a different color
    if (isUserReservation) {
      backgroundColor = "#2ecc71"; // green
    }

    // For different reservation statuses
    if (event.resource.status === "cancelled") {
      backgroundColor = "#e74c3c"; // red
    } else if (event.resource.status === "pending") {
      backgroundColor = "#f39c12"; // yellow
    }

    return {
      style: {
        backgroundColor,
        borderRadius: "4px",
        opacity: 0.8,
        color: "white",
        border: "0",
        display: "block",
      },
    };
  };

  if (loading) {
    return <Loading size="large" />;
  }

  if (error) {
    return <div className="p-4 bg-red-100 text-red-700 rounded">{error}</div>;
  }

  return (
    <div className="h-[70vh]">
      <Calendar
        localizer={localizer}
        events={events}
        startAccessor="start"
        endAccessor="end"
        style={{ height: "100%", width: "100%" }}
        onSelectEvent={handleEventSelect}
        eventPropGetter={eventStyleGetter}
        views={["month", "week", "day", "agenda"]}
        defaultView="month"
        popup
        tooltipAccessor={(event) => {
          const res = event.resource;
          return `${res.title} - Room: ${res.room_name || `#${res.room_id}`}`;
        }}
      />
    </div>
  );
};

export default ReservationCalendar;
