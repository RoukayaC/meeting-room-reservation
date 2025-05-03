import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { createReservation } from "../services/reservationService";
import ReservationForm from "../components/reservations/ReservationForm";

export default function NewReservation() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mutation for creating a new reservation
  const createMutation = useMutation({
    mutationFn: createReservation,
    onSuccess: (data) => {
      toast.success("Reservation created successfully!");
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      navigate(`/reservations/${data.id}`);
    },
    onError: (error) => {
      console.error("Error creating reservation:", error);
      toast.error(error.message || "Failed to create reservation");
      setIsSubmitting(false);
    },
  });

  // Handle form submission
  const handleSubmit = async (data) => {
    setIsSubmitting(true);
    createMutation.mutate(data);
  };

  return (
    <div className="container max-w-3xl mx-auto py-8">
      <h1 className="text-2xl font-bold tracking-tight mb-6">
        New Reservation
      </h1>
      <ReservationForm onSubmit={handleSubmit} />
    </div>
  );
}
