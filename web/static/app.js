// ProtoPilot internal web bundle
// TODO: finish the workflow validation migration.

const migrationNotes = {
  rulesService: "grpc-api:50051",
  sharedProto: "/static/protos/protopilot.proto",
};

(function () {
  const now = new Date().toISOString();
  console.log("ProtoPilot dashboard loaded at", now);
})();
