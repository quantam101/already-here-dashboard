type PaymentCancelledSearchParams = Promise<{ ref?: string }>;

export default async function PaymentCancelledPage({ searchParams }: { searchParams: PaymentCancelledSearchParams }) {
  const params = await searchParams;

  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Already Here LLC</p>
        <h1>Payment Not Completed</h1>
        <p className="subhead">The Stripe payment page was closed before completion. Your service record is not marked paid yet.</p>
        {params.ref && <p className="detail"><strong>Reference</strong><span>{params.ref}</span></p>}
      </section>
    </main>
  );
}
