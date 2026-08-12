import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customIntentsAPI } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type {
  CustomIntent,
  CustomIntentCreate,
  CustomIntentUpdate,
  CustomIntentTestResponse,
} from "@/lib/types/domain";

export function useCustomIntents() {
  const token = useAuthStore((s) => s.token);
  return useQuery<CustomIntent[]>({
    queryKey: ["customIntents"],
    queryFn: () => customIntentsAPI.list(token!),
    enabled: !!token,
  });
}

export function useCreateCustomIntent() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CustomIntentCreate) => customIntentsAPI.create(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customIntents"] });
    },
    onError: (error) => {
      console.error("Failed to create custom intent", error);
    },
  });
}

export function useUpdateCustomIntent() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustomIntentUpdate }) =>
      customIntentsAPI.update(token!, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customIntents"] });
    },
    onError: (error) => {
      console.error("Failed to update custom intent", error);
    },
  });
}

export function useDeleteCustomIntent() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => customIntentsAPI.delete(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customIntents"] });
    },
    onError: (error) => {
      console.error("Failed to delete custom intent", error);
    },
  });
}

export function useTestCustomIntent() {
  const token = useAuthStore((s) => s.token);
  return useMutation<CustomIntentTestResponse, Error, { prompt: string; intentIds?: string[] }>({
    mutationFn: ({ prompt, intentIds }) => customIntentsAPI.test(token!, prompt, intentIds),
  });
}
