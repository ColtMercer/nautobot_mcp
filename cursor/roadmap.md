# Roadmap for Nautobot FastMCP Server + Streamlit Chat

This roadmap outlines the steps required to complete the Nautobot FastMCP Server + Streamlit Chat project. Each step is designed to ensure that all requirements are met and that the project is delivered successfully.

## Phase 1: Initial Setup ✅


1. **Repository and CI Setup** ✅
   - ✅ Initialize the repository with a README and LICENSE.
   - ✅ Set up continuous integration with pre-commit hooks for linting, type checking, and testing.
   - ✅ Ensure the repository is ready for collaborative development.

2. **Docker Compose Setup** ✅
   - ✅ Create a `docker-compose.yml` file to define services for Nautobot, Postgres, Redis, FastMCP server, and Streamlit UI.
   - ✅ Configure health checks for each service to ensure they are running correctly.

3. **Environment Configuration** ✅
   - ✅ Create an `env.example` file with necessary environment variables.
   - ✅ Ensure sensitive information is not committed to the repository.

## Phase 2: Core Development ✅

4. **Data Seeding** ✅
   - ✅ Develop a seed container and script to populate Nautobot with demo data.
   - ✅ For demo data here are the requirements
     - ✅ Location hierarchy:
       - ✅ Location Type "Region" = NAM, ASPAC, EMEA, LATAM
       - ✅ Location Type "Country" under Regions = Top 5 countries in each region
       - ✅ Location Type "Campus" under Countries = 5 character Alphanumeric site code and two per country
       - ✅ Location Type "Data Center" under countries= 2 Locations Per Region
       - ✅ Location Type "Branch" under countries = 10 Locations Per Country
      - ✅ Devices should have a two WAN routers per campus / branch, A core router at every campus and 5 Access switches at each campus, an entire IP Fabric at every data center including 4 spine switches and 20 leaf switches
      - ⚠️ Interfaces - data center leaf should have ports connecting to spine and a single VLAN for compute data, each campus access should have uplinks to core, and user ports and vlan 100 for data and vlan 200 for voice, campus core should have uplinks to wan routers
      - ⚠️ IPAM - Each user vlan should have a /24 prefix on the VLAN interfaces and /31s on the uplinks, Leaf switches should have /24 for compute vlans and /31s on the spine uplinks, every prefix should be in the ipam associated with correct location and associated with the corresponding interfaces on bot the core/spine and access switch / leaf switch connected to them
      - ✅ device roles should be associated with the devices
      - ✅ The naming standard for devices should be <location_code>-<function_code><device_number>
        - ✅ function codes should be "acc" for access switches, "lea" for leaf, "spn" for spine, "wan" for wan, cor for Core, etc
        - ✅ devices numbering should be 1000 - 1999 for leaf numbers, 001 - 999 for access and core and wan etc
        - ✅ devices should be associated with right locations
   - ✅ Validate that GraphQL queries return expected results.

5. **FastMCP Server Development** ✅
   - ✅ Implement the FastMCP server skeleton with discovery and health endpoints.
   - ✅ Develop the `get_prefixes_by_location` tool and ensure it returns data for demo locations.
   - ✅ Implement the `llm_chat` tool to call other tools and emit citations.

6. **Streamlit Chat UI Development** ✅
   - ✅ Develop the Streamlit UI with features for server selection, tool catalog viewing, and chat interaction.
   - ✅ Implement export functionality for chat transcripts in JSON and Markdown formats.

## Phase 3: Testing and Observability ✅

7. **Testing Strategy Implementation** ✅
   - ✅ Write unit tests for tool handlers and GraphQL client error paths.
   - ✅ Develop contract tests to validate tool schemas and discovery responses.
   - ✅ Implement integration tests to ensure end-to-end functionality.
   - ✅ Conduct golden tests to verify chat exports.

8. **Observability Enhancements** ✅
   - ✅ Implement structured logging and metrics collection.
   - ⚠️ Set up a Prometheus endpoint for monitoring tool calls and errors (disabled due to conflicts).

## Phase 4: Security and Documentation ✅

9. **Security Enhancements** ✅
   - ✅ Implement API key protection for tool invocations.
   - ✅ Configure CORS and rate limiting as needed.

10. **Documentation and Examples** ✅
    - ✅ Write comprehensive documentation for developers and users.
    - ✅ Provide examples and sample exports to demonstrate functionality.

## Phase 5: Finalization and Deployment ✅

11. **Acceptance Testing** ✅
    - ✅ Conduct manual acceptance tests to ensure all requirements are met.
    - ✅ Verify that the system is stable and ready for deployment.

12. **Deployment Preparation** ✅
    - ✅ Prepare the system for deployment, ensuring all components are configured correctly.
    - ✅ Conduct a final review to ensure all project goals have been achieved.

---

This roadmap will guide the development process, ensuring that all requirements are met and that the project is delivered successfully. Each phase builds upon the previous one, leading to a comprehensive and well-tested solution. 