import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getReservationById, updateReservation } from "../services/reservationService";
import ReservationForm from "../components/reservations/ReservationForm";

export default function EditReservation() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Fetch the reservation
  const { data: reservation, isLoading, error } = useQuery({
    queryKey: ["reservation", id],
    queryFn: () => getReservationById(id),
  });
  
  // Mutation for updating the reservation
  const updateMutation = useMutation({
    mutationFn: (data) => updateReservation(id, data),
    onSuccess: () => {
      toast.success("Reservation updated successfully!");
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      queryClient.invalidateQueries({ queryKey: ["reservation", id] });
      navigate(`/reservations/${id}`);
    },
    onError: (error) => {
      console.error("Error updating reservation:", error);
      toast.error(error.message || "Failed to update reservation");
      setIsSubmitting(false);
    },
  });

  // Handle form submission
  const handleSubmit = async (data) => {
    setIsSubmitting(true);
    updateMutation.mutate(data);
  };

  if (isLoading) {
    return <div className="p-8">Loading reservation details...</div>;
  }

  if (error) {
    return (
      <div className="p-8">
        <h2 className="text-2xl font-bold">Error</h2>
        <p>Failed to load reservation details.</p>
      </div>
    );
  }

  if (!reservation) {
    return (
      <div className="p-8">
        <h2 className="text-2xl font-bold">Reservation Not Found</h2>
        <p>The reservation you're looking for doesn't exist.</p>
      </div>
    );
  }

  return (
    <div className="container max-w-3xl mx-auto py-8">
      <h1 className="text-2xl font-bold tracking-tight mb-6">
        Edit Reservation #{id}
      </h1>
      <ReservationForm reservation={reservation} onSubmit={handleSubmit} />
    </div>
  );
}
