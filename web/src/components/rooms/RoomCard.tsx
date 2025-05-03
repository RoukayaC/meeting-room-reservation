import { Link } from "react-router-dom";
import { Calendar, Users, Monitor, Eraser } from "lucide-react";
import { getColorFromString } from "../../lib/utils";
import { Room } from "../../types/models";

interface RoomCardProps {
  room: Room;
}

function RoomCard({ room }: RoomCardProps) {
  const {
    id,
    name,
    room_type,
    capacity,
    floor,
    building,
    has_projector,
    has_video_conf,
    has_whiteboard,
  } = room;

  // Generate a consistent color based on room type
  const typeColor = getColorFromString(room_type);

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      {/* Room type badge */}
      <div className={`${typeColor} h-2 w-full`}></div>

      <div className="p-6">
        <div className="flex justify-between items-start">
          {/* Room name and details */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">{name}</h3>
            <p className="text-sm text-gray-500">
              {building}, {floor} Floor
            </p>
          </div>

          {/* Room type badge */}
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize bg-gray-100 text-gray-800">
            {room_type}
          </span>
        </div>

        {/* Room features */}
        <div className="mt-4 flex items-center text-gray-700">
          <Users className="h-4 w-4 mr-1" />
          <span className="text-sm">{capacity} people</span>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          {has_projector && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              <Monitor className="h-3 w-3 mr-1" /> Projector
            </span>
          )}

          {has_video_conf && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <Monitor className="h-3 w-3 mr-1" /> Video Conference
            </span>
          )}

          {has_whiteboard && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
              <Eraser className="h-3 w-3 mr-1" /> Whiteboard
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-between">
          <Link
            to={`/rooms/${id}`}
            className="text-sm font-medium text-primary hover:text-primary-foreground"
          >
            View details
          </Link>

          <Link
            to={`/reservations/new?room=${id}`}
            className="flex items-center text-sm font-medium text-primary hover:text-primary-foreground"
          >
            <Calendar className="h-3 w-3 mr-1" />
            Book now
          </Link>
        </div>
      </div>
    </div>
  );
}

export default RoomCard;
