export type RiskSeverity = 'low' | 'medium' | 'high' | 'critical';
export type RiskStatus = 'open' | 'mitigating' | 'closed';

export interface Project {
  id: number;
  organisation: number;
  name: string;
  risk_score: number;
  created_at: string;
  updated_at: string;
  open_risks_count?: number;
}

export interface Risk {
  id: number;
  project: number;
  title: string;
  description: string;
  severity: RiskSeverity;
  status: RiskStatus;
  owner: string;
  created_at: string;
  updated_at: string;
}

export interface UpdateRiskPayload {
  title?: string;
  description?: string;
  severity?: RiskSeverity;
  status?: RiskStatus;
  owner?: string;
}

