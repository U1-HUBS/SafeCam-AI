import React from "react";
import Badge from "../ui/Badge";

export const AlertBadge = ({ severity = "critical" }) => {
  if (severity === "critical") {
    return <Badge variant="danger" pulse>CRITICAL THREAT</Badge>;
  }
  if (severity === "warning") {
    return <Badge variant="warning">WARNING</Badge>;
  }
  return <Badge variant="success">RESOLVED</Badge>;
};

export default AlertBadge;
