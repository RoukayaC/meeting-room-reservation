export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  department?: string;
  permissions?: string[];
}

export interface Room {
  id: number;
  name: string;
  room_type: string;
  capacity: number;
  floor: string;
  building?: string;
  has_projector: boolean;
  has_video_conf: boolean;
  has_whiteboard: boolean;
  description?: string;
}

export interface Attendee {
  id?: number;
  email: string;
  name?: string;
  user_id?: number;
  reservation_id?: number;
}

export interface Reservation {
  id: number;
  room_id: number;
  room_name?: string;
  user_id: number;
  start_time: string;
  end_time: string;
  status: string;
  purpose?: string;
  title?: string;
  description?: string;
  attendees?: Attendee[];
  attendees_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ReservationFormData {
  room_id: number;
  start_time: string;
  end_time: string;
  purpose?: string;
  attendees?: Attendee[];
}

export interface RoomUnavailability {
  id: number;
  room_id: number;
  start_time: string;
  end_time: string;
  reason: string;
}

export interface ApiError {
  error: {
    message: string;
    code?: string;
  };
}
