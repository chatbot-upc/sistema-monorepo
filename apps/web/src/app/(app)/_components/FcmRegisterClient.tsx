"use client";

import { useFcmRegister } from "@/lib/use-fcm-register";

export function FcmRegisterClient() {
  useFcmRegister();
  return null;
}
