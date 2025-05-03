import { useState } from "react";
import { RoomFilters, RoomType } from "../../types/models";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { Checkbox } from "../ui/checkbox";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

interface RoomFilterProps {
  onFilterChange: (filters: RoomFilters) => void;
  className?: string;
}

const ROOM_TYPES: { value: RoomType; label: string }[] = [
  { value: "meeting", label: "Meeting Room" },
  { value: "conference", label: "Conference Room" },
  { value: "office", label: "Office" },
  { value: "auditorium", label: "Auditorium" },
];

const RoomFilter: React.FC<RoomFilterProps> = ({
  onFilterChange,
  className = "",
}) => {
  const [capacity, setCapacity] = useState<number | undefined>(undefined);
  const [roomType, setRoomType] = useState<RoomType | undefined>(undefined);
  const [hasProjector, setHasProjector] = useState<boolean | undefined>(
    undefined
  );
  const [hasVideoConf, setHasVideoConf] = useState<boolean | undefined>(
    undefined
  );
  const [hasWhiteboard, setHasWhiteboard] = useState<boolean | undefined>(
    undefined
  );

  const handleCapacityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value ? parseInt(e.target.value, 10) : undefined;
    setCapacity(isNaN(value as number) ? undefined : value);
  };

  const handleTypeChange = (value: string) => {
    setRoomType(value as RoomType);
  };

  const handleProjectorChange = (checked: boolean) => {
    setHasProjector(checked ? true : undefined);
  };

  const handleVideoConfChange = (checked: boolean) => {
    setHasVideoConf(checked ? true : undefined);
  };

  const handleWhiteboardChange = (checked: boolean) => {
    setHasWhiteboard(checked ? true : undefined);
  };

  const handleFilterApply = () => {
    onFilterChange({
      capacity,
      type: roomType,
      has_projector: hasProjector,
      has_video_conf: hasVideoConf,
      has_whiteboard: hasWhiteboard,
    });
  };

  const handleReset = () => {
    setCapacity(undefined);
    setRoomType(undefined);
    setHasProjector(undefined);
    setHasVideoConf(undefined);
    setHasWhiteboard(undefined);

    onFilterChange({});
  };

  return (
    <div className={`p-4 border rounded-md bg-background ${className}`}>
      <h3 className="text-lg font-medium mb-4">Filter Rooms</h3>

      <div className="space-y-4">
        <div>
          <Label htmlFor="capacity">Minimum Capacity</Label>
          <Input
            id="capacity"
            type="number"
            min={1}
            placeholder="Any capacity"
            value={capacity || ""}
            onChange={handleCapacityChange}
          />
        </div>

        <div>
          <Label htmlFor="room-type">Room Type</Label>
          <Select value={roomType} onValueChange={handleTypeChange}>
            <SelectTrigger id="room-type">
              <SelectValue placeholder="Any type" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>Room Types</SelectLabel>
                {ROOM_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Features</Label>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="has-projector"
              checked={hasProjector === true}
              onCheckedChange={handleProjectorChange}
            />
            <Label htmlFor="has-projector" className="cursor-pointer">
              Projector
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="has-video-conf"
              checked={hasVideoConf === true}
              onCheckedChange={handleVideoConfChange}
            />
            <Label htmlFor="has-video-conf" className="cursor-pointer">
              Video Conferencing
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="has-whiteboard"
              checked={hasWhiteboard === true}
              onCheckedChange={handleWhiteboardChange}
            />
            <Label htmlFor="has-whiteboard" className="cursor-pointer">
              Whiteboard
            </Label>
          </div>
        </div>

        <div className="flex flex-col space-y-2 pt-2">
          <Button onClick={handleFilterApply}>Apply Filters</Button>
          <Button variant="outline" onClick={handleReset}>
            Reset Filters
          </Button>
        </div>
      </div>
    </div>
  );
};

export default RoomFilter;
