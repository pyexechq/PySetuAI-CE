import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { promptTemplatesAPI } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type {
  PromptTemplate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
  PromptVersionCreate,
} from "@/lib/types/domain";

export function usePromptTemplates() {
  const token = useAuthStore((s) => s.token);
  return useQuery<PromptTemplate[]>({
    queryKey: ["promptTemplates"],
    queryFn: () => promptTemplatesAPI.list(token!),
    enabled: !!token,
  });
}

export function usePromptTemplate(id: string) {
  const token = useAuthStore((s) => s.token);
  return useQuery<PromptTemplate>({
    queryKey: ["promptTemplates", id],
    queryFn: () => promptTemplatesAPI.get(token!, id),
    enabled: !!token && !!id,
  });
}

export function useCreatePromptTemplate() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PromptTemplateCreate) => promptTemplatesAPI.create(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] });
    },
    onError: (error) => {
      console.error("Failed to create prompt template", error);
    },
  });
}

export function useUpdatePromptTemplate() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PromptTemplateUpdate }) =>
      promptTemplatesAPI.update(token!, id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] });
      queryClient.invalidateQueries({ queryKey: ["promptTemplates", id] });
    },
    onError: (error) => {
      console.error("Failed to update prompt template", error);
    },
  });
}

export function useDeletePromptTemplate() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => promptTemplatesAPI.delete(token!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] });
    },
    onError: (error) => {
      console.error("Failed to delete prompt template", error);
    },
  });
}

export function useAddPromptVersion() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PromptVersionCreate }) =>
      promptTemplatesAPI.addVersion(token!, id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] });
      queryClient.invalidateQueries({ queryKey: ["promptTemplates", id] });
    },
    onError: (error) => {
      console.error("Failed to add prompt version", error);
    },
  });
}
