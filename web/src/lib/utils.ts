import { clsx, ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO, isToday as isDateToday } from 'date-fns';

/**
 * Merge multiple class names with tailwind-merge
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format date string to a more readable format
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "";
  
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM dd, yyyy');
  } catch (error) {
    console.error('Error formatting date:', error);
    return dateString;
  }
}

/**
 * Format time string (HH:MM) from a date
 */
export function formatTime(dateString: string | null | undefined): string {
  if (!dateString) return "";
  
  try {
    const date = parseISO(dateString);
    return format(date, 'h:mm a');
  } catch (error) {
    console.error('Error formatting time:', error);
    return dateString;
  }
}

/**
 * Format a date string to a readable date and time format
 */
export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return "";
  
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM dd, yyyy h:mm a');
  } catch (error) {
    console.error('Error formatting datetime:', error);
    return dateString;
  }
}

/**
 * Check if the provided date is today
 */
export function isToday(dateString: string | null | undefined): boolean {
  if (!dateString) return false;
  
  try {
    const date = parseISO(dateString);
    return isDateToday(date);
  } catch (error) {
    console.error('Error checking if date is today:', error);
    return false;
  }
}

/**
 * Convert a time string (HH:MM) to a Date object
 */
export function timeStringToDate(timeString: string | null, baseDate: Date = new Date()): Date | null {
  if (!timeString) return null;
  
  const [hours, minutes] = timeString.split(":").map(Number);
  const date = new Date(baseDate);
  date.setHours(hours, minutes, 0, 0);
  
  return date;
}

/**
 * Get a color based on a string (useful for generating consistent colors for entities)
 */
export function getColorFromString(str: string | null | undefined): string {
  if (!str) return "bg-blue-500";
  
  const colors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-yellow-500",
    "bg-purple-500",
    "bg-pink-500",
    "bg-indigo-500",
    "bg-red-500",
    "bg-orange-500",
    "bg-teal-500",
    "bg-cyan-500",
  ];
  
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  hash = Math.abs(hash);
  return colors[hash % colors.length];
}

/**
 * Convert a string to title case
 */
export function toTitleCase(str: string): string {
  return str
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Handle API errors and return a user-friendly message
 */
export function getErrorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null) {
    // Check for API error format
    if ('error' in error && typeof error.error === 'object' && error.error !== null && 'message' in error.error) {
      return error.error.message as string;
    }

    // Check for message property
    if ('message' in error && typeof error.message === 'string') {
      return error.message;
    }
  }
  
  return 'An unexpected error occurred';
}

/**
 * Get room features as a list
 */
export function getRoomFeatures(room: any): string[] {
  const features: string[] = [];
  
  if (room?.has_projector) features.push('Projector');
  if (room?.has_video_conf) features.push('Video Conferencing');
  if (room?.has_whiteboard) features.push('Whiteboard');
  
  return features;
}

/**
 * Create a URL for Google Calendar event
 */
export function createGoogleCalendarUrl(reservation: any): string {
  if (!reservation) return '';
  
  try {
    const startDate = parseISO(reservation.start_time);
    const endDate = parseISO(reservation.end_time);
    
    const startDateFormatted = format(startDate, "yyyyMMdd'T'HHmmss");
    const endDateFormatted = format(endDate, "yyyyMMdd'T'HHmmss");
    
    const title = encodeURIComponent(reservation.title || `Meeting in ${reservation.room_name || 'Room'}`);
    const description = encodeURIComponent(reservation.purpose || '');
    const location = encodeURIComponent(reservation.room_name || '');
    
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&dates=${startDateFormatted}/${endDateFormatted}&details=${description}&location=${location}`;
  } catch (error) {
    console.error('Error creating Google Calendar URL:', error);
    return '';
  }
}