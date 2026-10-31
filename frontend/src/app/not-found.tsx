'use client';

import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import Link from 'next/link';

export default function NotFound() {
  return (
    <Box sx={{ py: 8, textAlign: 'center' }}>
      <Typography variant="h2" sx={{ mb: 1, fontWeight: 700 }}>
        404
      </Typography>
      <Typography variant="body1" sx={{ color: 'text.secondary', mb: 3 }}>
        The requested page could not be found or access is restricted.
      </Typography>
      <Button component={Link} href="/" variant="contained">
        Back to Dashboard
      </Button>
    </Box>
  );
}

