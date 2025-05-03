import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Room, RoomFilters } from '../../types/models';
import { getRooms } from '../../services/roomService';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import Loading from '../ui/loading';
import RoomFilter from './RoomFilter';
import { useAuth } from '../../context/AuthContext';
import { getRoomFeatures } from '../../lib/utils';

const RoomsList = () => {
  const [loading, setLoading] = useState(true);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [filteredRooms, setFilteredRooms] = useState<Room[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { isAdmin } = useAuth();

  useEffect(() => {
    const fetchRooms = async () => {
      try {
        setLoading(true);
        const data = await getRooms();
        setRooms(data);
        setFilteredRooms(data);
      } catch (err) {
        setError('Failed to fetch rooms');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchRooms();
  }, []);

  const handleFilterChange = async (filters: RoomFilters) => {
    try {
      setLoading(true);
      const data = await getRooms(filters);
      setFilteredRooms(data);
    } catch (err) {
      setError('Failed to filter rooms');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="p-4 bg-red-100 text-red-700 rounded">
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold">Rooms</h2>
        {isAdmin && (
          <Button asChild>
            <Link to="/rooms/new">Add Room</Link>
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="md:col-span-1">
          <RoomFilter onFilterChange={handleFilterChange} />
        </div>

        <div className="md:col-span-3">
          {loading ? (
            <Loading size="large" className="mt-8" />
          ) : (
            <>
              {filteredRooms.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredRooms.map((room) => (
                    <Card key={room.id}>
                      <CardContent className="p-4">
                        <div className="flex flex-col h-full">
                          <div>
                            <h3 className="font-bold text-lg mb-1">{room.name}</h3>
                            <p className="text-sm text-gray-500 capitalize">
                              {room.room_type} • Floor {room.floor}
                            </p>
                            <p className="text-sm text-gray-700 my-2">
                              Capacity: {room.capacity} people
                            </p>
                            {room.building && (
                              <p className="text-sm text-gray-500">{room.building}</p>
                            )}
                          </div>

                          <div className="flex flex-wrap gap-1 my-2">
                            {getRoomFeatures(room).map((feature, index) => (
                              <span
                                key={index}
                                className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                              >
                                {feature}
                              </span>
                            ))}
                          </div>

                          <div className="mt-auto pt-3">
                            <div className="flex justify-between">
                              <Button variant="outline" asChild>
                                <Link to={`/rooms/${room.id}`}>View Details</Link>
                              </Button>
                              <Button asChild>
                                <Link to={`/reservations/new?roomId=${room.id}`}>Reserve</Link>
                              </Button>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center p-8 border rounded-md">
                  <p className="text-lg text-gray-500">No rooms found matching your criteria</p>
                  {isAdmin && (
                    <Button className="mt-4" asChild>
                      <Link to="/rooms/new">Add New Room</Link>
                    </Button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default RoomsList;
